"use strict";
let checksum = 0;
for (let i = 0; i < 10000; i++) {
  checksum = (checksum + ((i * 7) % 97)) | 0;
}
if (checksum !== 479820) throw new Error("Wrong result: " + checksum);
const marker = "HERMES_SHARED_OK=" + checksum;
if (typeof console !== "undefined" && typeof console.log === "function") {
  console.log(marker);
} else if (typeof print === "function") {
  print(marker);
} else {
  throw new Error("No print sink");
}
