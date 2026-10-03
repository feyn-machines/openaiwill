export {};

declare global {
  interface Window {
    /**
     * Where a kind of work currently sits on the overview globe, in viewport
     * pixels. Set while the overview is mounted, so the module below it can
     * start its marks from the globe's columns.
     */
    __oawProjectWork?: (workId: string) => [number, number] | null;
  }
}
