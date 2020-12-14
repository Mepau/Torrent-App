Proyecto BitTorrent para Sistema Operativo 2

Este proyecto es un intento personal de abordar el protocolo BitTorrent y emplearlo en un sistema distribuido peer to peer hecho en Python. En el tiempo previsto se ha buscado no solo implementar el protocolo BitTorrent en practicamente toda su extension, pero la comunicacion y descarga de archivos utilizando peer to peer.

Para simular todo el sistema se han construido tres scripts principales en Python 3.9 para reconstruir todo el proceso de conexion a una red de peers via un tracker y un archivo metainfo torrent.


Probado usando python 3.9.

En Windows usar interpretador de venv:
```console
    venv\Scripts\activate
```  

Comando en Windows ejecutar servidor Web script:
```console
    python webserver.py
```
Acceder via browser a la ruta encontrada dentro del script que por default es ```http://ip:puerto/path_to/BACCHUS.torrent``` u otro metodo favorito para iniciar la descarga del archivo. El archivo tmabien se recreara en la ruta ```./torrents/BACCHUS.torrent``` 

Comando en Windows ejecutar tracker service script:
```console
    python tracker.py
```

Comando en Windows ejecutar Downloader/Peer script:
```console
    python downloader.py
```

Por default esta todo configurado para ser ejecutado en localhost puertos 9000, 9005 y 9200 respectivamente.

Tambien se ha configurado ( levemente hardcoded ) el primer Seeder que compartira el archivo y que deberia de iniciar como Peer en puerto 9010

Se ha intentado implementar para soportar tanto torrent de archivos unicos o de multiples archivos, debido a cuestiones de tiempo se ha reducido el soporte del ultimo hasta crear archivos torrent, mientras que el primero ( un unico archivo ) se ha cubrido un poco mas hasta intentar compartir bloques.

Actualmente los peers son capaces de realizar handshake y compartir los campos bitfield ( en caso de tener archivo que compartir ).

Breve Reporte de experiencia
--------------------------

Este proyecto ha sido el mas complejo en relacion a Sistemas Distribuidos hasta ahora de los que he podido participar. Como protocolo ya detallado ha sido relativamente facil interpretar la informacion, implementarlo en cambio ha requerido de haber adquirido aun mas conocimiento en el lenguaje de programacion utilizado Python que sin duda ha sido de ayuda pero resulto en un camino mucho mas dificil.

El proyecto en si es mas elaborado y de hecho veo facilmente como puede ser base de otros sistemas mucho mas complejo ya que provee de por si provee conceptos que pueden ser utilizados para coordinacion misma del sistema peer to peer.

Problemas encontrados
--------------------------

Utilizando Visual Studio Code encontraba situaciones inexplicables donde debia realizar prints a pantalla solo para que realmente el valor de las variables sea el real al ser comunicado via TCP. Debido a propia inexperiancia en el lenguaje y el tiempo de entrega no pude profundizar en el tema y solo lo planteo de esta manera.



