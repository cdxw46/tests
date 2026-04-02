import { WASI, File, OpenFile, ConsoleStdout, PreopenDirectory } from '@bjorn3/browser_wasi_shim'

export const getSigned = async (email, ca) => {
    let stderr = '';
    let stdout = '';

    const args = 'openssl cms -verify -in /email.eml -CAfile /ca.crt'.split(' ');
    const env = [];
    const fds = [
        new OpenFile(new File([])),
        ConsoleStdout.lineBuffered(line => stdout += line + '\n'),
        ConsoleStdout.lineBuffered(line => stderr += line),
        new PreopenDirectory('/', [
            ['email.eml', new File(new TextEncoder('utf-8').encode(email))],
            ['ca.crt', new File(new TextEncoder('utf-8').encode(ca))]
        ])
    ];

    const wasi = new WASI(args, env, fds, { debug: false });

    const wasm = await WebAssembly.instantiateStreaming(fetch('/wasm/openssl.wasm'), {
        wasi_snapshot_preview1: wasi.wasiImport
    });

    const exit = wasi.start(wasm.instance);

    return exit === 0 && stderr.trim() === 'CMS Verification successful' ? stdout : null;
}