import { defineConfig } from 'vite'
import { dirname } from 'path';
import { lstatSync, readdirSync } from 'fs';

let htmlFiles = Object.create(null);

for (const file of readdirSync(dirname(new URL(import.meta.url).pathname))) {
	if (file.endsWith('.html') && lstatSync(file).isFile()) {
		htmlFiles[file.replace('.html', '')] = file;
	}
}

export default defineConfig({
	build: {
		target: 'es2022',
		rollupOptions: {
			input: htmlFiles
		}
	}
})