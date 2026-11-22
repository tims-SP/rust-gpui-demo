use anyhow::{Result, ensure};
use gpui::{div, px, rgb, size, AppContext, Context, HeadlessAppContext, IntoElement, ParentElement, Render, Styled, Window};
use gpui_wgpu::{CosmicTextSystem, WgpuHeadlessRenderer};
use std::{cell::Cell, env, fs::File, io::{self, BufWriter, Write}, rc::Rc, sync::Arc, time::Instant};

const LINES: [&str; 5] = ["潮汐之间", "晚风把海面翻成一页蓝", "灯影随浪慢慢靠岸", "听见夜色深处的回响", "我们沿着微光向前"];
struct LyricsView { frame: Rc<Cell<u32>>, fps: u32, width: u32 }

impl Render for LyricsView {
    fn render(&mut self, _: &mut Window, _: &mut Context<Self>) -> impl IntoElement {
        let frame = self.frame.get();
        let scale = self.width as f32 / 1280.;
        let row = (frame / (3 * self.fps)) as usize % (LINES.len() - 2);
        let phase = (frame % (3 * self.fps)) as f32 / (3 * self.fps) as f32;
        let s = |v: f32| px(v * scale);
        let mut words = div().flex().flex_row().text_size(s(56.));
        let count = LINES[row+1].chars().count();
        for (index, ch) in LINES[row+1].chars().enumerate() {
            let color = if index as f32 <= phase * count as f32 { 0xdcf8ed } else { 0x788fa4 };
            words = words.child(div().text_color(rgb(color)).child(ch.to_string()));
        }
        div().size_full().bg(rgb(0x102537)).flex().flex_col().justify_center().px(s(80.))
            .gap(s(26.)).font_family("Noto Sans CJK SC")
            .child(div().text_size(s(21.)).text_color(rgb(0x94cece)).child("WHALE AUDIO LIBRARY"))
            .child(div().text_size(s(36.)).text_color(rgb(0x788fa4)).child(LINES[row]))
            .child(words)
            .child(div().text_size(s(36.)).text_color(rgb(0x788fa4)).child(LINES[row+2]))
            .child(div().w(s(1120.)).h(s(5.)).bg(rgb(0x384d60)).child(
                div().h(s(5.)).w(s(1120.*phase)).bg(rgb(0x8de2ce))))
    }
}

fn main() -> Result<()> {
    let args: Vec<_> = env::args().collect();
    ensure!(args.len()==6, "width height fps frames timings.csv; raw RGBA on stdout");
    let (w,h,fps,n): (u32,u32,u32,u32)=(args[1].parse()?,args[2].parse()?,args[3].parse()?,args[4].parse()?);
    ensure!(w>0 && h>0 && fps>0 && n>0);
    let mut cx=HeadlessAppContext::with_platform(Arc::new(CosmicTextSystem::new("Noto Sans CJK SC")),Arc::new(()),
        || Ok(Some(Box::new(WgpuHeadlessRenderer::new()?))));
    let counter=Rc::new(Cell::new(0));
    let state=counter.clone();
    let window=cx.open_window(size(px(w as f32),px(h as f32)),move |_,app| app.new(|_| LyricsView{frame:state,fps,width:w}))?;
    cx.simulate_window_scale_factor_change(window.into(), 1.0);
    cx.run_until_parked();
    let mut out=io::stdout().lock();
    let mut csv=BufWriter::new(File::create(&args[5])?);
    writeln!(csv,"frame,scene_ms,capture_ms,write_ms")?;
    for index in 0..n {
        counter.set(index);
        let start=Instant::now();
        cx.update_window(window.into(), |_,win,app| {
            win.refresh();
            win.draw(app).clear(app);
        })?;
        let scene=Instant::now();
        let rgba=cx.capture_screenshot(window.into())?;
        let ready=Instant::now();
        ensure!(rgba.dimensions()==(w,h),"unexpected dimensions {:?}",rgba.dimensions());
        out.write_all(rgba.as_raw())?;
        let done=Instant::now();
        writeln!(csv,"{index},{:.4},{:.4},{:.4}",(scene-start).as_secs_f64()*1e3,(ready-scene).as_secs_f64()*1e3,(done-ready).as_secs_f64()*1e3)?;
    }
    csv.flush()?;
    Ok(())
}
