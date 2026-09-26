() => {
  const x = DLL.liste[DLL.i], img = $('dllImg').getBoundingClientRect(), path = $('dllSvg').querySelectorAll('path')[1];
  const pr = path.getBoundingClientRect();
  const xs = x.contour ? x.contour.map(p => p[0]) : [x.box.x, x.box.x + x.box.w], ys = x.contour ? x.contour.map(p => p[1]) : [x.box.y, x.box.y + x.box.h];
  const att = { l: img.left + Math.min(...xs) * img.width, t: img.top + Math.min(...ys) * img.height, r: img.left + Math.max(...xs) * img.width, b: img.top + Math.max(...ys) * img.height };
  return { ecart: Math.max(Math.abs(pr.left - att.l), Math.abs(pr.top - att.t), Math.abs(pr.right - att.r), Math.abs(pr.bottom - att.b)),
           svg_sur_img: Math.abs($('dllSvg').getBoundingClientRect().width - img.width) < 1.5 && Math.abs($('dllSvg').getBoundingClientRect().left - img.left) < 1.5,
           trait: path.getAttribute('stroke'), qui: x.qui, voile: !!$('dllSvg').querySelector('rect[mask]'),
           nw: $('dllImg').naturalWidth, deborde: document.documentElement.scrollWidth > document.documentElement.clientWidth,
           cadre_ok: $('dllCadre').getBoundingClientRect().bottom <= $('dllScene').getBoundingClientRect().bottom + 1 };
}