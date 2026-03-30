# PicoCTF - Disko 4 (Forensics)

## Flag

```
picoCTF{d3l_d0n7_h1d3_w3ll_bc352004}
```

## Descripción del reto

Se proporciona un archivo comprimido `disko-4.dd.gz` que contiene una imagen de disco raw.

## Proceso de resolución

### 1. Descargar y descomprimir la imagen

```bash
wget -O disko-4.dd.gz "https://challenge-files.picoctf.net/c_plain_mesa/7ccb9163cdca38fb1317009dbfc22c0e268ffc4fe4deedd13fb4ffab2bd30731/disko-4.dd.gz"
gunzip -k disko-4.dd.gz
```

### 2. Identificar el sistema de archivos

```bash
file disko-4.dd
# DOS/MBR boot sector, OEM-ID "mkfs.fat", FAT (32 bit)
```

La imagen es un sistema de archivos **FAT32** de 100 MB.

### 3. Analizar el sistema de archivos con Sleuth Kit

```bash
fsstat disko-4.dd
```

Se identificó un sistema FAT32 con logs del sistema (directorio `/log`).

### 4. Listar archivos (incluyendo eliminados)

```bash
fls -r disko-4.dd
```

Se encontró un archivo **eliminado** marcado con `*`:
```
r/r * 532021:    dont-delete.gz
```

El archivo `dont-delete.gz` fue borrado del sistema de archivos pero sus datos seguían en el disco.

### 5. Recuperar el archivo eliminado

```bash
icat disko-4.dd 532021 > dont-delete.gz
gunzip -k dont-delete.gz
cat dont-delete
```

Resultado:
```
Here is your flag
picoCTF{d3l_d0n7_h1d3_w3ll_bc352004}
```

## Herramientas utilizadas

- **Sleuth Kit** (`fls`, `icat`, `fsstat`): Análisis forense del sistema de archivos FAT32
- **gunzip**: Descompresión de archivos gzip
- **file**: Identificación del tipo de archivo

## Concepto clave

El reto demuestra que **eliminar un archivo en FAT32 no borra los datos del disco**. Solo se marca la entrada del directorio como eliminada. Usando herramientas forenses como `fls` (para listar archivos eliminados) e `icat` (para extraer datos por inode), se pueden recuperar archivos "borrados".
