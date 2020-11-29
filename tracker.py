from http.server import HTTPServer, BaseHTTPRequestHandler
from torrent_parser import to_torrent
from piece_gen import pieces_gen
from urllib.parse import urlparse

PORT = 9005
tracker_addr = ("localhost", PORT)
tracking_file = ""
torrent_file = "./torrents/BACCHUS.torrent"


class trackerHandler(BaseHTTPRequestHandler):
    def do_GET(self):

        parsed_url = urlparse(self.path)

        print(parsed_url)

        self.send_response(202)
        output = b"Recibido"
        self.wfile.write(output)


def run_tracker():

    tracker = HTTPServer(tracker_addr, trackerHandler)
    print("[TRACKER] Tracker escuchando puerto %s" % PORT)
    tracker.serve_forever()


if __name__ == "__main__":
    run_tracker()
