"""Send the GPUI MP4 as pre-encoded H.264 over two local ICE/DTLS/SRTP peers."""
import asyncio, fractions, hashlib, json, math, pathlib, sys, time
import av
from aiortc import RTCPeerConnection, RTCConfiguration, RTCRtpSender, VideoStreamTrack
from aiortc.mediastreams import MediaStreamError

def p(values, q):
    return round(sorted(values)[math.ceil(len(values)*q)-1],3)

class Packets(VideoStreamTrack):
    def __init__(self, path):
        super().__init__()
        self.container=av.open(path)
        # Convert MP4 length-prefixed NAL units and prepend codec configuration for IDR frames.
        self.bsf=av.BitStreamFilterContext('h264_mp4toannexb', self.container.streams.video[0])
        self.frames=(out for packet in self.container.demux(video=0) if packet.size for out in self.bsf.filter(packet))
        self.sent={}
        self.t0=None
        self.first_pts=None
        self.ended=False
    async def recv(self):
        packet=next(self.frames,None)
        if packet is None:
            self.ended=True
            # A trailing access unit lets the receiver's jitter buffer release the last measured frame.
            # aiortc delivers H.264 on the next timestamp change. The extra packet is an actual IDR.
            if getattr(self,'trailer',None) is not None:
                last=self.trailer
                self.trailer=None
                last.pts=last.dts=self.last_pts+self.step
                last.time_base=self.base
                await asyncio.sleep(float(self.step*self.base))
                return last
            await asyncio.sleep(1)
            raise MediaStreamError
        packet.time_base=self.container.streams.video[0].time_base
        if self.t0 is None:
            self.base=packet.time_base
            self.first_pts=packet.pts
            self.t0=time.perf_counter()
            self.last_pts=packet.pts
            self.step=1
            self.trailer=av.Packet(bytes(packet))
        elif packet.pts>self.last_pts:
            self.step=packet.pts-self.last_pts
        self.last_pts=packet.pts
        elapsed=(packet.pts-self.first_pts)*self.base
        await asyncio.sleep(max(0,self.t0+float(elapsed)-time.perf_counter()))
        self.sent[round(elapsed*90000)]=time.perf_counter()
        return packet

def digest(frame):
    plane=frame.reformat(format='yuv420p').planes[0]
    buf=memoryview(plane)
    h=hashlib.sha256()
    for y in range(plane.height):
        start=y*plane.line_size
        h.update(buf[start:start+plane.width])
    return h.digest()

async def main(path):
    with av.open(path) as source:
        ref={round(frame.pts*frame.time_base*90000):digest(frame) for frame in source.decode(video=0)}
    pc1,pc2=(RTCPeerConnection(RTCConfiguration(iceServers=[])) for _ in range(2))
    track=Packets(path); delays=[]; correct=0;seen=set()
    try:
        tx=pc1.addTransceiver(track,direction='sendonly')
        tx.setCodecPreferences([c for c in RTCRtpSender.getCapabilities('video').codecs if c.mimeType=='video/H264'])
        future=asyncio.get_running_loop().create_future()
        @pc2.on('track')
        def incoming(remote):
            future.set_result(remote)
        await pc1.setLocalDescription(await pc1.createOffer())
        await pc2.setRemoteDescription(pc1.localDescription)
        await pc2.setLocalDescription(await pc2.createAnswer())
        await pc1.setRemoteDescription(pc2.localDescription)
        remote=await asyncio.wait_for(future,10)
        async with asyncio.timeout(60):
            while len(seen)<len(ref):
                frame=await remote.recv()
                finish=time.perf_counter()
                ts=round(frame.pts*frame.time_base*90000)
                assert ts in ref and ts not in seen,ts
                seen.add(ts)
                delays.append((finish-track.sent[ts])*1000)
                correct+=int(digest(frame)==ref[ts])
        stats=await pc2.getStats()
        inbound=next(s for s in stats.values() if s.type=='inbound-rtp')
        transport=next(s for s in stats.values() if s.type=='transport')
        report=dict(clip=pathlib.Path(path).name,frames=len(ref),decoded=len(seen),matching_luma=correct,codec='H264',dtls=transport.dtlsState,packets_received=inbound.packetsReceived,packets_lost=inbound.packetsLost,send_to_decode_ms_p50=p(delays,.5),send_to_decode_ms_p95=p(delays,.95),send_to_decode_ms_p99=p(delays,.99))
        print('RTC',json.dumps(report),flush=True)
        assert correct==len(ref) and report['dtls']=='connected'
        pathlib.Path(path).with_suffix('.rtc.json').write_text(json.dumps(report,indent=2))
    finally:
        await asyncio.gather(pc1.close(),pc2.close())
        track.container.close()
asyncio.run(main(sys.argv[1]))
