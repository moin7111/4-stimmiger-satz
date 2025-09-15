declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}

declare module "react" {
  const React: any;
  export default React;
  export function useState<S = any>(initialState: S): [S, (v: S) => void];
  export function useMemo<T = any>(factory: () => T, deps: any[]): T;
  export const StrictMode: any;
  export const useEffect: any;
  export const useRef: any;
  export type ChangeEvent<T = any> = any;
}

declare module "react-dom/client" {
  export function createRoot(container: any): { render: (node: any) => void };
}

declare module "vexflow" {
  export const Flow: any;
}

declare module "react/jsx-runtime" {
  export const jsx: any;
  export const jsxs: any;
  export const Fragment: any;
}

