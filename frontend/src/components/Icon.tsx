const paths = {
  build: 'm14 4 6 6-9 9H5v-6l9-9ZM12 6l6 6M4 21h16',
  step: 'm5 4 11 8-11 8V4Zm14 0v16',
  play: 'm6 4 13 8-13 8V4Z',
  pause: 'M8 4v16M16 4v16',
  reset: 'M3 11a9 9 0 1 1 3 8M3 4v7h7',
  sun: 'M12 3v2m0 14v2M3 12h2m14 0h2M5.6 5.6 7 7m10 10 1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  moon: 'M20 14a8 8 0 0 1-10-10A8 8 0 1 0 20 14Z',
  chip: 'M6 6h12v12H6V6Zm3 3h6v6H9V9ZM9 2v4m6-4v4M9 18v4m6-4v4M2 9h4m-4 6h4m12-6h4m-4 6h4',
  book: 'M12 5v16M3 4h5l4 2 4-2h5v15h-5l-4 2-4-2H3V4Z',
} as const;

export function Icon({ name }: { name: keyof typeof paths }) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}
