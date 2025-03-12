// import {Loader2} from "lucide-react";
import favicon from "../../assets/Favicon-contexton.svg";

const LoadingView = () => {
  return (
    <div className="ml-12 flex flex-col gap-4 animate-fade-in animate-once">
      {/* Top part with logo and animated dots */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <img src={favicon} className="animate-pulse animate-infinite" />
          <div className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-primary animate-ping animate-infinite" />
        </div>
        <p className="text-lg font-medium">CortexOn is working on your task</p>
        <div className="flex space-x-1 ml-1">
          <div className="h-2 w-2 rounded-full bg-primary animate-bounce animate-infinite" />
          <div className="h-2 w-2 rounded-full bg-primary animate-bounce animate-infinite animate-delay-150" />
          <div className="h-2 w-2 rounded-full bg-primary animate-bounce animate-infinite animate-delay-300" />
        </div>
      </div>

      {/* Middle part with animated steps
      <div className="ml-6 pl-4 border-l-2 border-muted">
        <div className="flex flex-col gap-3 max-w-lg">
          <div className="flex items-center gap-2 animate-pulse animate-infinite animate-duration-1000">
            <Loader2
              size={16}
              className="text-primary animate-spin animate-infinite"
            />
            <span className="text-muted-foreground text-sm">
              Analyzing input data...
            </span>
          </div>
          <div className="flex items-center gap-2 animate-pulse animate-infinite animate-duration-1000 animate-delay-300">
            <Loader2
              size={16}
              className="text-primary animate-spin animate-infinite"
            />
            <span className="text-muted-foreground text-sm">
              Generating solution steps...
            </span>
          </div>
          <div className="flex items-center gap-2 animate-pulse animate-infinite animate-duration-1000 animate-delay-600">
            <Loader2
              size={16}
              className="text-primary animate-spin animate-infinite"
            />
            <span className="text-muted-foreground text-sm">
              Running code executor...
            </span>
          </div>
        </div>
      </div>

      Bottom part with progress bar
      <div className="mt-2 w-full max-w-md">
        <div className="h-1 w-full bg-muted rounded-full overflow-hidden">
          <div className="h-full bg-primary rounded-full animate-pulse animate-infinite animate-duration-2000 w-2/3" />
        </div>
      </div> */}
    </div>
  );
};

export default LoadingView;
