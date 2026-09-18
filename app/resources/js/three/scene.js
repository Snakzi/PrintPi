/* Pieces the three.js views share: the bed grid, camera framing and cleanup. */

import { BufferAttribute, BufferGeometry, Color, Group, LineBasicMaterial, LineSegments, SRGBColorSpace, Vector3 } from 'three';

export const GRID_STEP = 10;

// Looking at the bed from front-right, slightly above; the printer's front is -Y.
export const VIEW_DIRECTION = new Vector3(0.8, -1, 0.7).normalize();

/** The printable area of a profile bed ({ x, y, centered }) as { minX, minY, sizeX, sizeY }. */
export function bedArea(bed) {
  if (!bed) return null;
  return {
    minX: bed.centered ? -bed.x / 2 : 0,
    minY: bed.centered ? -bed.y / 2 : 0,
    sizeX: bed.x,
    sizeY: bed.y,
  };
}

/**
 * A colour of the current theme for three.js: the CSS variable resolved through the page and read
 * back through a canvas, since the palette is written in oklch, which three cannot parse.
 */
export function themeColor(variable) {
  const probe = document.createElement('span');
  probe.style.color = `var(${variable})`;
  document.body.appendChild(probe);
  const style = getComputedStyle(probe).color;
  probe.remove();
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 1;
  const context = canvas.getContext('2d');
  context.fillStyle = style;
  context.fillRect(0, 0, 1, 1);
  const [r, g, b] = context.getImageData(0, 0, 1, 1).data;
  return new Color().setRGB(r / 255, g / 255, b / 255, SRGBColorSpace);
}

/** Marks a material as wearing a theme colour, so retint() can follow a theme switch. */
export function themed(material, variable) {
  material.userData.themeColor = variable;
  material.color.copy(themeColor(variable));
  return material;
}

/** Re-resolves every themed material below the object after the theme changed. */
export function retint(object) {
  object.traverse((child) => {
    const variable = child.material?.userData?.themeColor;
    if (variable) child.material.color.copy(themeColor(variable));
  });
}

export function gridLines(coordinates, variable) {
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new BufferAttribute(Float32Array.from(coordinates), 3));
  return new LineSegments(geometry, themed(new LineBasicMaterial(), variable));
}

/** A 10 mm grid with stronger lines every 50 mm and an outline, drawn at Z 0. */
export function bedGrid({ minX, minY, sizeX, sizeY }) {
  const minor = [];
  const major = [];
  for (let gx = 0; gx <= sizeX; gx += GRID_STEP) {
    (gx % 50 === 0 ? major : minor).push(minX + gx, minY, 0, minX + gx, minY + sizeY, 0);
  }
  for (let gy = 0; gy <= sizeY; gy += GRID_STEP) {
    (gy % 50 === 0 ? major : minor).push(minX, minY + gy, 0, minX + sizeX, minY + gy, 0);
  }
  const maxX = minX + sizeX;
  const maxY = minY + sizeY;
  const outline = [minX, minY, 0, maxX, minY, 0, maxX, minY, 0, maxX, maxY, 0, maxX, maxY, 0, minX, maxY, 0, minX, maxY, 0, minX, minY, 0];
  const group = new Group();
  group.add(gridLines(minor, '--color-zinc-800'), gridLines(major, '--color-zinc-700'), gridLines(outline, '--color-zinc-500'));
  return group;
}

/** Place the camera so the box fills the view from the standard direction; padding below 1 crops the bounding sphere. */
export function fitCamera(camera, controls, box, { direction = VIEW_DIRECTION, padding = 1.15 } = {}) {
  const center = box.getCenter(new Vector3());
  const radius = Math.max(box.getSize(new Vector3()).length() / 2, 5);
  const distance = (radius / Math.sin((camera.fov * Math.PI) / 360)) * padding;
  camera.position.copy(center).addScaledVector(direction, distance);
  camera.near = Math.max(distance / 200, 0.1);
  camera.far = distance * 20;
  camera.updateProjectionMatrix();
  if (controls) {
    controls.target.copy(center);
    controls.update();
  } else {
    camera.lookAt(center);
  }
}

export function disposeObject(object) {
  object.traverse((child) => {
    child.geometry?.dispose();
    child.material?.dispose();
  });
}
