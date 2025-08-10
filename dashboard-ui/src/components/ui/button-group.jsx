import * as React from "react";
import { cn } from "../../lib/utils";

const ButtonGroup = React.forwardRef(
  ({ className, children, ...props }, ref) => (
    <div
      className={cn("inline-flex rounded-md shadow-sm", className)}
      ref={ref}
      {...props}
    >
      {children}
    </div>
  )
);
ButtonGroup.displayName = "ButtonGroup";

const ButtonGroupItem = React.forwardRef(
  ({ className, active, children, ...props }, ref) => (
    <button
      className={cn(
        "relative inline-flex items-center px-3 py-2 text-sm font-medium transition-colors",
        "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        "focus:z-10 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        "first:rounded-l-md last:rounded-r-md",
        "[&:not(:first-child)]:border-l-0",
        active && "bg-primary text-primary-foreground hover:bg-primary/90",
        className
      )}
      ref={ref}
      {...props}
    >
      {children}
    </button>
  )
);
ButtonGroupItem.displayName = "ButtonGroupItem";

export { ButtonGroup, ButtonGroupItem };
