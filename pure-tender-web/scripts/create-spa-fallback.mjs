import { copyFile, access, constants } from "node:fs/promises";

const distIndex = new URL("../dist/index.html", import.meta.url);
const dist404 = new URL("../dist/404.html", import.meta.url);

await access(distIndex, constants.F_OK);
await copyFile(distIndex, dist404);

console.log("Created dist/404.html from dist/index.html");
