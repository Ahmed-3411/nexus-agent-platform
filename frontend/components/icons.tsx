import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function Icon({ children, ...props }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      {children}
    </svg>
  );
}

export const Icons = {
  grid: (props: IconProps) => <Icon {...props}><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></Icon>,
  plus: (props: IconProps) => <Icon {...props}><path d="M12 5v14M5 12h14"/></Icon>,
  pulse: (props: IconProps) => <Icon {...props}><path d="M3 12h4l2.2-6 4.1 12 2.2-6H21"/></Icon>,
  chart: (props: IconProps) => <Icon {...props}><path d="M4 19V9M10 19V5M16 19v-7M22 19V3"/></Icon>,
  logout: (props: IconProps) => <Icon {...props}><path d="M10 17l5-5-5-5M15 12H3M15 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4"/></Icon>,
  arrow: (props: IconProps) => <Icon {...props}><path d="M5 12h14M14 7l5 5-5 5"/></Icon>,
  check: (props: IconProps) => <Icon {...props}><path d="m5 12 4 4L19 6"/></Icon>,
  x: (props: IconProps) => <Icon {...props}><path d="m6 6 12 12M18 6 6 18"/></Icon>,
  clock: (props: IconProps) => <Icon {...props}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></Icon>,
  layers: (props: IconProps) => <Icon {...props}><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/></Icon>,
  shield: (props: IconProps) => <Icon {...props}><path d="M12 3 4.5 6v5.5c0 4.5 3.1 7.9 7.5 9.5 4.4-1.6 7.5-5 7.5-9.5V6L12 3Z"/><path d="m9 12 2 2 4-4"/></Icon>,
  menu: (props: IconProps) => <Icon {...props}><path d="M4 7h16M4 12h16M4 17h16"/></Icon>,
  refresh: (props: IconProps) => <Icon {...props}><path d="M20 6v5h-5M4 18v-5h5"/><path d="M6.1 9a7 7 0 0 1 11.5-2.6L20 11M4 13l2.4 4.6A7 7 0 0 0 17.9 15"/></Icon>,
  workflow: (props: IconProps) => <Icon {...props}><rect x="3" y="3" width="6" height="6" rx="2"/><rect x="15" y="15" width="6" height="6" rx="2"/><path d="M9 6h3a6 6 0 0 1 6 6v3M15 18h-3a6 6 0 0 1-6-6V9"/></Icon>,
};
