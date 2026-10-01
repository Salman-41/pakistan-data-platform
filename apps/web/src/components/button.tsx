import * as React from 'react';
import {Slot} from '@radix-ui/react-slot';
import {clsx} from 'clsx';
import {twMerge} from 'tailwind-merge';
/** Local shadcn-style primitive: semantic HTML by default; Slot supports links. */
export const Button=React.forwardRef<HTMLButtonElement,React.ButtonHTMLAttributes<HTMLButtonElement>&{asChild?:boolean}>(({className,asChild=false,...props},ref)=>{const Comp=asChild?Slot:'button';return <Comp className={twMerge(clsx('button',className))} ref={ref} {...props}/>});
Button.displayName='Button';
