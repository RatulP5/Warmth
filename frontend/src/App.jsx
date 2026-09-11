import { useEffect, useRef } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Lenis from 'lenis'
import gsap from 'gsap'

import DashboardLayout from './components/layouts/DashboardLayout.jsx'
import Dashboard from './pages/dashboard.jsx'
import Alerts from './pages/Alerts.jsx'
import Analytics from './pages/Analytics.jsx'
import WardIntelligence from './pages/WardIntelligence.jsx'
import AagaamIntro from './components/intro/AagaamIntro.jsx'

function CommandCentre() {
  const cursorRef = useRef(null)

  useEffect(() => {
    // 1. Initialize Lenis Smooth Scroll
    const lenis = new Lenis({ duration: 1.2, easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)) })
    function raf(time) {
      lenis.raf(time)
      requestAnimationFrame(raf)
    }
    requestAnimationFrame(raf)

    // 2. Custom Magnetic Pointer
    const cursor = cursorRef.current
    const onMouseMove = (e) => {
      gsap.to(cursor, {
        x: e.clientX,
        y: e.clientY,
        duration: 0.2,
        ease: 'power2.out'
      })
    }
    window.addEventListener('mousemove', onMouseMove)

    return () => {
      lenis.destroy()
      window.removeEventListener('mousemove', onMouseMove)
    }
  }, [])

  return (
    <div>
      {/* Custom Glow Cursor */}
      <div 
        ref={cursorRef} 
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '20px',
          height: '20px',
          borderRadius: '50%',
          backgroundColor: '#ff5500',
          pointerEvents: 'none',
          zIndex: 9999,
          mixBlendMode: 'difference',
          transform: 'translate(-50%, -50%)'
        }}
      />
      <DashboardLayout>
        <Routes>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/ward-intelligence" element={<WardIntelligence />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </DashboardLayout>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AagaamIntro />} />
      <Route path="/*" element={<CommandCentre />} />
    </Routes>
  )
}
