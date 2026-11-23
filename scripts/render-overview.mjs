import { readFileSync, writeFileSync } from 'node:fs';
import { COLS, frame, look } from '../.profile-renderer/src/display/dmd.ts';
import { slideshow } from '../.profile-renderer/src/display/slides.ts';

const data = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const facts = [
  ['PUBLIC REPOS', data.public_repos, 'INCLUDING FORKS'],
  ['ORIGINAL REPOS', data.original_repos, 'OWN PUBLIC PROJECTS'],
  ['STARS EARNED', data.original_stars, 'ORIGINAL REPOS ONLY'],
];
const style = {
  look: { ...look('amber', 'dark', true), unlitOpacity: 0.025 },
  dots: true,
  grid: true,
  animations: true,
  background: '#0d1117',
};
const number = new Intl.NumberFormat('en-US');
const slides = facts.map(([label, value, note]) => {
  const count = number.format(value);
  return [
    { text: label, col: 4, row: 5 },
    { text: count, col: 4, row: 24, scale: count.length > 7 ? 2 : 3, shine: true },
    { text: note, col: 4, row: 58, dim: true },
  ];
});
const display = slideshow('brooklyn', slides, { col: 0, row: 1, cols: COLS, rows: 71 },
  style, ['type', 'push', 'wipe']);
const svg = frame({
  title: 'Public GitHub overview',
  desc: facts.map(([label, value, note]) => `${label}: ${value} (${note})`).join('. '),
  ...style,
  css: display.css,
  body: `<defs>${display.defs}</defs>${display.markup}`,
});
writeFileSync('assets/metrics/overview.svg', svg);
