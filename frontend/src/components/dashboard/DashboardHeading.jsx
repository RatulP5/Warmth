import { useEffect, useRef } from "react";
import { gsap } from "gsap";

const phrases = [
  "SEE HEAT BEFORE IT HARMS",
  "SPATIAL DATA SAVED LIVES",
  "PREDICTIVE THERMAL INTELLIGENCE",
];

export default function DashboardHeading() {
  const headingRef = useRef(null);
  const textRef = useRef(null);
  const cursorRef = useRef(null);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      textRef.current.textContent = phrases[0];
      return;
    }

    const ctx = gsap.context(() => {
      const text = textRef.current;

      // Controls how fast the typing happens
      const typeSpeed = 0.1;

      // Controls how fast the backspace happens
      const deleteSpeed = 0.08;

      const timeline = gsap.timeline({
        repeat: -1,
      });

      phrases.forEach((phrase) => {
        const typingProxy = { value: 0 };

        // TYPE
        timeline.to(typingProxy, {
          value: phrase.length,
          duration: phrase.length * typeSpeed,
          ease: "none",

          onStart: () => {
            text.textContent = "";
          },

          onUpdate: () => {
            const length = Math.floor(typingProxy.value);
            text.textContent = phrase.slice(0, length);
          },
        });

        // HOLD
        timeline.to({}, {
          duration: 2,
        });

        // BACKSPACE
        const deleteProxy = { value: phrase.length };

        timeline.to(deleteProxy, {
          value: 0,
          duration: phrase.length * deleteSpeed,
          ease: "none",

          onUpdate: () => {
            const length = Math.ceil(deleteProxy.value);
            text.textContent = phrase.slice(0, length);
          },
        });

        // Small pause before next phrase
        timeline.to({}, {
          duration: 0.5,
        });
      });
    }, headingRef);

    return () => ctx.revert();
  }, []);

  return (
    <header className="dashboard-heading" ref={headingRef}>
      <div className="dashboard-heading__eyebrow">
        <span
          className="dashboard-heading__status-dot"
          aria-hidden="true"
        />
        LIVE HEAT INTELLIGENCE
      </div>

      <h1 className="dashboard-heading__headline">
        <span className="typing-line">
          <span ref={textRef}></span>
          <span
            ref={cursorRef}
            className="dashboard-heading__cursor"
            aria-hidden="true"
          >
            |
          </span>
        </span>
      </h1>

      <p className="dashboard-heading__location">
        KOLKATA · 141-WARD THERMAL INTELLIGENCE
      </p>
    </header>
  );
}