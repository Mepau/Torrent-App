import os
import bencodepy

# Recursively obtain all files within nested directories
def rread_dir(fp):
    files = []

    dir_files = os.listdir(fp)

    if len(dir_files) > 0:
        for file in dir_files:
            file_fpath = "".join([fp, "/", file])
            if os.path.isdir(file_fpath):
                files.append(rread_dir(file_fpath))
            elif os.path.isfile(file_fpath):
                files.append(
                    {"path": file_fpath, "length": os.path.getsize(file_fpath)}
                )

        return files


def flatten_list(nested_lists):
    flat_list = []
    for sublist in nested_lists:
        if isinstance(sublist, list):
            for item in sublist:
                flat_list.append(item)
                # print(item)
        elif isinstance(sublist, dict):
            flat_list.append(sublist)
    return flat_list


def to_torrent(filepath, tracker_url, stringed_hashes, piece_length):
    # En caso de que la ruta de archivo apunte a un directorio
    if os.path.isdir(filepath):
        files = os.listdir(filepath)
        if len(files) > 0:
            # En caso de encontrar multiples archivos
            if len(files) > 1:
                # Estructura diccionario a ser codificado de manera Bencode

                files_dict = {
                    "announce": tracker_url,
                    "info": {
                        "files": [],
                        "name": os.path.basename(filepath),
                        "piece length": piece_length,
                        "pieces": stringed_hashes,
                    },
                }
                for file in files:
                    file_fpath = "".join([filepath, "/", file])
                    if os.path.isdir(file_fpath):
                        # Encontrar todos los archivos no directorio
                        # dentro del directorio del archivo raiz
                        files = flatten_list(rread_dir(file_fpath))
                        if len(files) > 0:
                            files_dict["info"]["files"].append(files)
                        else:
                            print(f"Directorio {file_fpath} esta vacio")
                    elif os.path.isfile(file_fpath):
                        files_dict["info"]["files"].append(
                            {"path": file_fpath, "length": os.path.getsize(file_fpath)}
                        )

                flatten_files = flatten_list(files_dict["info"]["files"])
                files_dict["info"]["files"] = []

                # Convierte las rutas de archivo a lista
                # Se omite el primer nodo de la ruta/lista resultante
                for file in flatten_files:
                    listed_path = file["path"].split("/")
                    files_dict["info"]["files"].append(
                        {"path": listed_path[1:], "length": file["length"]}
                    )

                return bencodepy.encode(files_dict)

    # To torrent a single file
    elif os.path.isfile(filepath):

        file_dict = {
            "announce": tracker_url,
            "info": {
                "length": os.path.getsize(filepath),
                "name": os.path.basename(filepath),
                "piece length": piece_length,
                "pieces": stringed_hashes,
            },
        }

        return bencodepy.encode(file_dict)


def from_torrent():
    pass
