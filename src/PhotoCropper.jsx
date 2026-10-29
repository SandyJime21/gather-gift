import { useCallback, useEffect, useRef, useState } from 'react';
import { Button, Form, Modal } from 'react-bootstrap';

const VIEW = 280;
const OUT = 512;
const KEEPS_ALPHA = /^image\/(png|webp|gif)$/;

function CropModal({ file, onDone, onCancel }) {
  const [img, setImg] = useState(null);
  const [src, setSrc] = useState('');
  const [zoom, setZoom] = useState(1);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const drag = useRef(null);

  useEffect(() => {
    let cancelled = false;
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => { if (!cancelled) { setSrc(url); setImg(image); } };
    image.onerror = () => { if (!cancelled) onDone(file); };
    image.src = url;
    return () => { cancelled = true; URL.revokeObjectURL(url); };
  }, [file]);

  const base = img ? VIEW / Math.min(img.naturalWidth, img.naturalHeight) : 1;
  const clamp = (p, z) => {
    if (!img) return p;
    const s = base * z;
    const mx = Math.max(0, (img.naturalWidth * s - VIEW) / 2);
    const my = Math.max(0, (img.naturalHeight * s - VIEW) / 2);
    return { x: Math.min(mx, Math.max(-mx, p.x)), y: Math.min(my, Math.max(-my, p.y)) };
  };
  const changeZoom = (value) => {
    const z = Math.min(4, Math.max(1, value));
    setZoom(z);
    setPos((p) => clamp(p, z));
  };
  const nudge = (dx, dy) => setPos((p) => clamp({ x: p.x + dx, y: p.y + dy }, zoom));

  const save = () => {
    const s = base * zoom;
    const w = img.naturalWidth * s;
    const h = img.naturalHeight * s;
    const ratio = OUT / VIEW;
    const canvas = document.createElement('canvas');
    canvas.width = OUT;
    canvas.height = OUT;
    const ctx = canvas.getContext('2d');
    const keepAlpha = KEEPS_ALPHA.test(file.type);
    if (!keepAlpha) { ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, OUT, OUT); }
    ctx.drawImage(img, (VIEW / 2 - w / 2 + pos.x) * ratio, (VIEW / 2 - h / 2 + pos.y) * ratio, w * ratio, h * ratio);
    const type = keepAlpha ? 'image/png' : 'image/jpeg';
    canvas.toBlob((blob) => {
      if (!blob) { onDone(file); return; }
      const name = file.name.replace(/\.[^.]+$/, '') + (keepAlpha ? '.png' : '.jpg');
      onDone(new File([blob], name, { type }));
    }, type, 0.92);
  };

  const s = base * zoom;
  const w = img ? img.naturalWidth * s : 0;
  const h = img ? img.naturalHeight * s : 0;
  return (
    <Modal show onHide={onCancel} centered>
      <Modal.Header closeButton><Modal.Title>Position your photo</Modal.Title></Modal.Header>
      <Modal.Body className="photo-crop-body">
        <p className="small text-secondary">Drag the photo to move it and use the slider to zoom. The circle is what will show.</p>
        <div
          className="photo-crop-view"
          style={{ width: VIEW, height: VIEW }}
          tabIndex={0}
          role="application"
          aria-label="Photo position. Use arrow keys to move and plus or minus to zoom."
          onPointerDown={(e) => { e.currentTarget.setPointerCapture?.(e.pointerId); drag.current = { x: e.clientX, y: e.clientY, start: pos }; }}
          onPointerMove={(e) => { if (drag.current) setPos(clamp({ x: drag.current.start.x + e.clientX - drag.current.x, y: drag.current.start.y + e.clientY - drag.current.y }, zoom)); }}
          onPointerUp={() => { drag.current = null; }}
          onPointerCancel={() => { drag.current = null; }}
          onWheel={(e) => changeZoom(zoom - e.deltaY * 0.002)}
          onKeyDown={(e) => {
            const moves = { ArrowLeft: [10, 0], ArrowRight: [-10, 0], ArrowUp: [0, 10], ArrowDown: [0, -10] };
            if (moves[e.key]) { e.preventDefault(); nudge(...moves[e.key]); }
            if (e.key === '+' || e.key === '=') changeZoom(zoom + 0.1);
            if (e.key === '-') changeZoom(zoom - 0.1);
          }}
        >
          {img && <img src={src} alt="" draggable={false} style={{ width: w, height: h, left: VIEW / 2 - w / 2 + pos.x, top: VIEW / 2 - h / 2 + pos.y }} />}
        </div>
        <Form.Group controlId="photo-crop-zoom" className="photo-crop-zoom">
          <Button title="Zoom out to show more of the photo inside the circle." type="button" variant="outline-secondary" size="sm" aria-label="Zoom out" onClick={() => changeZoom(zoom - 0.2)}>−</Button>
          <Form.Range min={1} max={4} step={0.01} value={zoom} aria-label="Zoom" onChange={(e) => changeZoom(Number(e.target.value))} />
          <Button title="Zoom in to make the photo larger inside the circle." type="button" variant="outline-secondary" size="sm" aria-label="Zoom in" onClick={() => changeZoom(zoom + 0.2)}>+</Button>
        </Form.Group>
      </Modal.Body>
      <Modal.Footer>
        <Button title="Close the photo editor without replacing your saved photo." variant="outline-secondary" onClick={onCancel}>Cancel</Button>
        <Button title="Save the photo with the position and zoom shown in the preview." variant="success" disabled={!img} onClick={save}>Use this photo</Button>
      </Modal.Footer>
    </Modal>
  );
}

// crop(file) resolves to the cropped File, or null when cancelled.
export function usePhotoCrop() {
  const [job, setJob] = useState(null);
  const crop = useCallback((file) => {
    if (!file || typeof URL.createObjectURL !== 'function') return Promise.resolve(file || null);
    return new Promise((resolve) => setJob({ file, resolve }));
  }, []);
  const finish = (result) => { job.resolve(result); setJob(null); };
  const cropper = job ? <CropModal key={job.file.name + job.file.size} file={job.file} onDone={finish} onCancel={() => finish(null)} /> : null;
  return { crop, cropper };
}
