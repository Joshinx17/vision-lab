"""Loopback-only static UI and bounded JSON API. Never acquires a webcam."""
import json
import logging
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, unquote

from .config import ROOT, settings, local_path
from .service import SignService

LOG = logging.getLogger(__name__)
MAX_BODY = 4_100_000


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        LOG.debug(fmt, *args)

    def json(self, status, value):
        data = json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def allowed(self):
        hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        host = self.headers.get('Host')
        origin = self.headers.get('Origin')
        return host in hosts and (origin is None or origin in {f'http://{h}' for h in hosts})

    def do_GET(self):
        if not self.allowed():
            return self.json(403, {'error': 'Local same-origin requests only.'})
        path = urlsplit(self.path).path
        if path == '/api/status':
            return self.json(200, self.server.service.status())
        if path == '/api/health':
            return self.json(200, {'status': 'ok', 'application': 'Vision-Lab'})
        static = ROOT / 'frontend' / 'dist'
        target = (static / unquote(path).lstrip('/')).resolve()
        if not target.is_relative_to(static.resolve()):
            return self.json(403, {'error': 'Invalid path.'})
        if path == '/':
            target = static / 'index.html'
        if not target.is_file():
            return self.json(404, {'error': 'File not found. Build the frontend with npm run build.'})
        data = target.read_bytes()
        mime = 'application/javascript' if target.suffix == '.js' else mimetypes.guess_type(target)[0] or 'application/octet-stream'
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if not self.allowed() or self.headers.get('X-Vision-Lab') != '1':
            return self.json(403, {'error': 'Local same-origin requests only.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY or self.headers.get('Content-Type') != 'application/json':
                return self.json(413, {'error': 'Expected JSON body under 4.1 MB.'})
            self.connection.settimeout(15)
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('Expected JSON object.')
            service = self.server.service
            routes = {
                '/api/sign/load': lambda: self.load_sign(),
                '/api/sign/predict': lambda: service.predict(body),
                '/api/sign/close': lambda: self.close_sign(),
                '/api/dataset/capture': lambda: service.capture(body),
                '/api/train': lambda: service.start_training(body),
            }
            route = routes.get(self.path)
            if not route:
                return self.json(404, {'error': 'Unknown endpoint.'})
            if service.job['state'] == 'running' and self.path != '/api/dataset/capture':
                return self.json(409, {'error': 'Training is running. Wait for completion.'})
            return self.json(200, route())
        except (ValueError, TypeError) as error:
            LOG.warning('Request rejected: %s', error)
            self.json(400, {'error': str(error)})
        except ImportError:
            LOG.exception('Missing dependency')
            self.json(503, {'error': 'Python dependencies missing. Install requirements.txt.'})
        except Exception:
            LOG.exception('Frame service failure')
            self.json(500, {'error': 'Processing failed. See logs/vision-lab.log.'})

    def load_sign(self):
        with self.server.service.lock:
            self.server.service.load()
        return {'loaded': True}

    def close_sign(self):
        self.server.service.close()
        return {'closed': True}


def main():
    config = settings()
    logs = local_path('logs')
    logs.mkdir(exist_ok=True)
    from logging.handlers import RotatingFileHandler
    logging.basicConfig(level=config['log_level'], format='%(asctime)s %(levelname)s %(name)s %(message)s', handlers=[logging.StreamHandler(), RotatingFileHandler(logs / 'vision-lab.log', maxBytes=2_000_000, backupCount=2)])
    server = ThreadingHTTPServer(('127.0.0.1', config['port']), Handler)
    server.service = SignService(config['model'])
    LOG.info('Vision-Lab ready at http://localhost:%s', config['port'])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.service.close()
        LOG.info('Shutdown complete')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(f'Vision-Lab startup failed: {error}')
