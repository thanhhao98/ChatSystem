import * as React from "react"
import { motion, useReducedMotion } from "framer-motion"
import { cn } from "@/lib/utils"
import { Button, type ButtonProps } from "@/components/ui/button"

export interface HeroAction {
  label: string
  href: string
  variant?: ButtonProps["variant"]
  onClick?: React.MouseEventHandler<HTMLAnchorElement>
}

export interface HeroProps extends Omit<React.HTMLAttributes<HTMLElement>, "title"> {
  gradient?: boolean
  blur?: boolean
  isChatFocused?: boolean
  isFocused?: boolean
  compact?: boolean
  title?: React.ReactNode
  subtitle?: React.ReactNode
  actions?: HeroAction[]
  titleClassName?: string
  subtitleClassName?: string
  actionsClassName?: string
  contentClassName?: string
  children?: React.ReactNode
}

const Hero = React.forwardRef<HTMLElement, HeroProps>(
  (
    {
      className,
      gradient = true,
      blur = true,
      isChatFocused = false,
      isFocused,
      compact = false,
      title,
      subtitle,
      actions,
      titleClassName,
      subtitleClassName,
      actionsClassName,
      contentClassName,
      children,
      ...props
    },
    ref,
  ) => {
    const prefersReducedMotion = useReducedMotion()
    const active = isFocused !== undefined ? isFocused : isChatFocused

    const lampTransition = React.useMemo(
      () => ({
        duration: prefersReducedMotion ? 0 : 0.65,
        ease: "easeInOut" as const,
      }),
      [prefersReducedMotion],
    )

    return (
      <section
        ref={ref}
        data-lamp-state={active ? "focused" : "idle"}
        className={cn(
          "relative z-0 flex min-h-[80vh] w-full flex-col items-center justify-center overflow-hidden rounded-md bg-white dark:bg-background text-foreground transition-colors duration-300",
          className,
        )}
        {...props}
      >
        {gradient && (
          <div
            aria-hidden="true"
            className={cn(
              "pointer-events-none absolute top-0 isolate z-0 flex w-full flex-1 items-start justify-center transition-opacity duration-500",
              compact ? "opacity-35 scale-y-75 origin-top" : "opacity-100",
            )}
          >
            {blur && (
              <div className="pointer-events-none absolute top-0 z-50 h-48 w-full bg-transparent opacity-10 backdrop-blur-md" />
            )}

            {/* Main glow: #FFE88A Baby Chick Yellow in Light Mode, primary white in Dark Mode */}
            <motion.div
              initial={false}
              animate={{
                width: active ? "32rem" : "18rem",
                opacity: active ? 0.85 : 0.5,
              }}
              transition={lampTransition}
              className="pointer-events-none absolute inset-auto z-50 h-36 max-w-[85vw] -translate-y-[-30%] rounded-full bg-[#FFE88A]/65 dark:bg-primary/60 blur-3xl"
            />

            {/* Lamp effect: #FFE88A Baby Chick Yellow in Light Mode, primary white in Dark Mode */}
            <motion.div
              initial={false}
              animate={{
                width: active ? "28rem" : "10rem",
                opacity: active ? 0.9 : 0.55,
              }}
              transition={lampTransition}
              className="pointer-events-none absolute top-0 z-30 h-36 max-w-[78vw] -translate-y-[20%] rounded-full bg-[#FFE88A]/60 dark:bg-primary/60 blur-2xl"
            />

            {/* Top line: #F2D45C Baby Chick Yellow in Light Mode, primary white in Dark Mode */}
            <motion.div
              initial={false}
              animate={{
                width: active ? "32rem" : "14rem",
                opacity: active ? 1 : 0.8,
              }}
              transition={lampTransition}
              className="pointer-events-none absolute inset-auto z-50 h-[2.5px] dark:h-0.5 max-w-[88vw] -translate-y-[-10%] rounded-full bg-[#F2D45C] shadow-[0_1px_12px_rgba(242,212,92,0.65)] dark:bg-primary/80 dark:shadow-none"
            />

            {/* Left gradient cone: #FFF4BD in Light Mode, primary white in Dark Mode */}
            <motion.div
              initial={false}
              animate={{
                opacity: active ? 1 : 0.55,
                width: active ? "32rem" : "15rem",
              }}
              transition={lampTransition}
              style={{
                backgroundImage: `conic-gradient(var(--conic-position), var(--tw-gradient-stops))`,
              }}
              className={cn(
                "pointer-events-none absolute inset-auto right-1/2 h-56 max-w-[46vw] overflow-visible bg-gradient-conic [--conic-position:from_70deg_at_center_top]",
                "[--tw-gradient-stops:rgba(255,232,138,0.45)_0%,rgba(255,244,189,0.35)_24%,rgba(255,244,189,0)_50%,transparent_100%]",
                "dark:from-primary/60 dark:via-transparent dark:to-transparent",
              )}
            >
              <div className="pointer-events-none absolute bottom-0 left-0 z-20 h-40 w-full bg-white dark:bg-background transition-colors duration-300 [mask-image:linear-gradient(to_top,white,transparent)]" />
              <div className="pointer-events-none absolute bottom-0 left-0 z-20 h-full w-24 sm:w-40 bg-white dark:bg-background transition-colors duration-300 [mask-image:linear-gradient(to_right,white,transparent)]" />
            </motion.div>

            {/* Right gradient cone: #FFF4BD in Light Mode, primary white in Dark Mode */}
            <motion.div
              initial={false}
              animate={{
                opacity: active ? 1 : 0.55,
                width: active ? "32rem" : "15rem",
              }}
              transition={lampTransition}
              style={{
                backgroundImage: `conic-gradient(var(--conic-position), var(--tw-gradient-stops))`,
              }}
              className={cn(
                "pointer-events-none absolute inset-auto left-1/2 h-56 max-w-[46vw] overflow-visible bg-gradient-conic [--conic-position:from_290deg_at_center_top]",
                "[--tw-gradient-stops:transparent_0%,rgba(255,244,189,0)_50%,rgba(255,244,189,0.35)_76%,rgba(255,232,138,0.45)_100%]",
                "dark:from-transparent dark:via-transparent dark:to-primary/60",
              )}
            >
              <div className="pointer-events-none absolute bottom-0 right-0 z-20 h-full w-24 sm:w-40 bg-white dark:bg-background transition-colors duration-300 [mask-image:linear-gradient(to_left,white,transparent)]" />
              <div className="pointer-events-none absolute bottom-0 right-0 z-20 h-40 w-full bg-white dark:bg-background transition-colors duration-300 [mask-image:linear-gradient(to_top,white,transparent)]" />
            </motion.div>
          </div>
        )}

        <motion.div
          initial={prefersReducedMotion ? false : { y: 24, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{
            ease: "easeInOut",
            duration: prefersReducedMotion ? 0 : 0.6,
          }}
          className={cn(
            "relative z-50 container flex flex-1 flex-col items-center justify-center gap-6 px-4 sm:px-6 md:px-10 pt-28 pb-10",
            contentClassName,
          )}
        >
          {(title || subtitle || (actions && actions.length > 0)) && (
            <div className="flex flex-col items-center text-center space-y-3 max-w-3xl">
              {title && (
                <h1
                  className={cn(
                    "text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight text-foreground",
                    titleClassName,
                  )}
                >
                  {title}
                </h1>
              )}
              {subtitle && (
                <p
                  className={cn(
                    "text-sm sm:text-base md:text-lg text-muted-foreground max-w-2xl",
                    subtitleClassName,
                  )}
                >
                  {subtitle}
                </p>
              )}
              {actions && actions.length > 0 && (
                <div className={cn("flex flex-wrap justify-center gap-4", actionsClassName)}>
                  {actions.map((action, index) => (
                    <Button
                      key={index}
                      variant={action.variant || "default"}
                      asChild
                    >
                      <a href={action.href} onClick={action.onClick}>
                        {action.label}
                      </a>
                    </Button>
                  ))}
                </div>
              )}
            </div>
          )}

          {children}
        </motion.div>
      </section>
    )
  },
)
Hero.displayName = "Hero"

export { Hero }
