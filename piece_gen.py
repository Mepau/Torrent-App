import os
import hashlib
from torrent_parser import flatten_list, rread_dir
from constants import DEF_BLOCK_LENGTH, DEF_PIECE_LENGTH


def pieces_gen(fpath, piece_length=DEF_PIECE_LENGTH):
    # Dividir multiples archivos en bloques/piezas
    pieces = []
    pieces_hash = []
    piece = b""
    if os.path.isdir(fpath):
        files = os.listdir(fpath)
        scanned_files = []
        if len(files) > 0:
            # En caso de encontrar multiples archivos
            if len(files) > 1:
                for file in files:
                    nested_file_fpath = "".join([fpath, "/", file])
                    if os.path.isdir(nested_file_fpath):
                        # Encontrar todos los archivos no directorio
                        # dentro del directorio del archivo raiz
                        files = flatten_list(rread_dir(nested_file_fpath))
                        if len(files) > 0:
                            scanned_files.append(files)
                        else:
                            print(
                                f"[ADVERTENCIA] Directorio {nested_file_fpath} esta vacio"
                            )
                    elif os.path.isfile(nested_file_fpath):
                        scanned_files.append(
                            {
                                "path": nested_file_fpath,
                                "length": os.path.getsize(nested_file_fpath),
                            }
                        )
                flatten_flist = flatten_list(scanned_files)

                for file in flatten_flist:
                    with open(file["path"], "rb") as open_file:
                        counter = 0
                        while counter < file["length"]:
                            piece = open_file.read(piece_length)
                            pieces.append(piece)
                            # print(f"Nueva pieza {piece}")
                            pieces_hash.append(hashlib.sha1(piece).digest())
                            counter += len(piece)

    # Piezas de un solo archivo
    elif os.path.isfile(fpath):
        file_size = os.path.getsize(fpath)
        counter = 0

        with open(fpath, "rb") as open_file:
            while counter < file_size:
                piece = open_file.read(piece_length)
                pieces.append(piece)
                # print(f"Nueva pieza {piece}")
                pieces_hash.append(hashlib.sha1(piece).digest())
                counter += len(piece)

    return pieces, pieces_hash


def gen_block(piece, start_offset, block_length=DEF_BLOCK_LENGTH):

    piece_length = len(piece)

    if start_offset + block_length > piece_length:
        return piece[start_offset:piece_length]
    else:
        return piece[start_offset : start_offset + block_length]


def piece_toblocks(piece, block_length=DEF_BLOCK_LENGTH):

    blocks = [
        {"block_start": x, "block": piece[x : x + block_length], "length": block_length}
        for x in range(len(piece))
        if x % block_length == 0
    ]

    return blocks
