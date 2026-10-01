export function transformSeries(rows: {period:string; value:number}[], mode:string): {period:string;value:number|null}[];
export function csv(rows: Record<string, unknown>[]):string;
