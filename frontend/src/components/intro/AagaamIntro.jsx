import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import gsap from "gsap";
import "./AagaamIntro.css";

export default function AagaamIntro() {
  const introRef = useRef(null);
  const navigate = useNavigate();
  const enterCommandCentre = () => navigate("/dashboard");

  useEffect(() => {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const context = gsap.context(() => {
      const elements = gsap.utils.toArray("[data-intro-reveal]");

      if (reduceMotion) {
        gsap.set(elements, { autoAlpha: 1, y: 0 });
        return;
      }

      const timeline = gsap.timeline({ defaults: { ease: "power2.out" } });
      timeline
        .to(".aagaam-intro__word", { autoAlpha: 1, y: 0, duration: 0.8 })
        .to(".aagaam-intro__latin", { autoAlpha: 1, y: 0, duration: 0.5 }, "-=0.35")
        .to(".aagaam-intro__meaning--bn", { autoAlpha: 1, x: 0, duration: 0.42 }, "+=0.28")
        .to(".aagaam-intro__meaning--hi", { autoAlpha: 1, x: 0, duration: 0.42 }, "+=0.2")
        .to(".aagaam-intro__meaning--en", { autoAlpha: 1, x: 0, duration: 0.42 }, "+=0.2")
        .to(".aagaam-intro__origins", { autoAlpha: 0, y: -14, duration: 0.38 }, "+=0.65")
        .to(".aagaam-intro__statement", { autoAlpha: 1, y: 0, duration: 0.68 }, "-=0.05")
        .to(".aagaam-intro__heatshield", { autoAlpha: 1, y: 0, duration: 0.45 }, "+=0.35")
        .to(".aagaam-intro__subtitle", { autoAlpha: 1, y: 0, duration: 0.4 }, "-=0.2")
        .to(".aagaam-intro__actions", { autoAlpha: 1, y: 0, duration: 0.4 }, "+=0.2");
    }, introRef);

    return () => context.revert();
  }, []);

  return (
    <main className="aagaam-intro" ref={introRef}>
      <div className="aagaam-intro__atmosphere" aria-hidden="true" />
      <button className="aagaam-intro__skip" onClick={enterCommandCentre} aria-label="Skip intro and enter command centre">
        Skip
      </button>

      <section className="aagaam-intro__content" aria-label="Aagaam introduction">
        <div className="aagaam-intro__origins">
          <h1 className="aagaam-intro__word" data-intro-reveal>আগাম</h1>
          <p className="aagaam-intro__latin" data-intro-reveal>AAGAAM</p>
          <div className="aagaam-intro__meanings" aria-label="Aagaam means in advance">
            <p className="aagaam-intro__meaning aagaam-intro__meaning--bn" data-intro-reveal>বাংলায় বলি — আগাম</p>
            <p className="aagaam-intro__meaning aagaam-intro__meaning--hi" data-intro-reveal>हिंदी में कहते हैं — पहले से</p>
            <p className="aagaam-intro__meaning aagaam-intro__meaning--en" data-intro-reveal>In English — in advance</p>
          </div>
        </div>

        <div className="aagaam-intro__destination">
          <p className="aagaam-intro__statement" data-intro-reveal>BEFORE THE HEAT HITS,<br />WE KNOW WHERE.</p>
          <p className="aagaam-intro__heatshield" data-intro-reveal>HEATSHIELD INDIA</p>
          <p className="aagaam-intro__subtitle" data-intro-reveal>Predictive Thermal Intelligence for Cities</p>
          <div className="aagaam-intro__actions" data-intro-reveal>
            <button className="aagaam-intro__enter" onClick={enterCommandCentre} aria-label="Enter HeatShield India command centre">
              ENTER COMMAND CENTRE <span aria-hidden="true">→</span>
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
