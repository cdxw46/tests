import { WASI, File, OpenFile, ConsoleStdout, PreopenDirectory } from '@bjorn3/browser_wasi_shim'

const parser = new WebAssembly.Module(await (await fetch('/wasm/parser.wasm')).arrayBuffer());

export const parse = async (email) => {
    let stdout = '';

    const args = ['parser'];
    const env = [];
    const fds = [
        new OpenFile(new File([])),
        ConsoleStdout.lineBuffered(line => stdout += line + '\n'),
        ConsoleStdout.lineBuffered(() => {}),
        new PreopenDirectory('/', [
            ['email.eml', new File(new TextEncoder('utf-8').encode(email))],
        ])
    ]

    const wasi = new WASI(args, env, fds, { debug: false });

    const instance = await WebAssembly.instantiate(parser, {
        wasi_snapshot_preview1: wasi.wasiImport
    });

    wasi.start(instance);
    
    return JSON.parse(stdout);
}