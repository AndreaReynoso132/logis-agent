import { useState, useRef, useEffect } from "react"
import axios from "axios"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import {
  Send, RefreshCw, Package, AlertTriangle, BarChart2,
  TrendingDown, DollarSign, Wrench, FlaskConical,
  Flame, Settings, Box, Wifi, WifiOff, Clock, Menu, X
} from "lucide-react"
import logo from "./assets/logo.png"
import "./App.css"

interface Message {
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

const API_URL = "http://localhost:8000"

const EJEMPLOS = [
  { icon: Package,       text: "¿Qué stock tengo de elaion f50 5w-40 4l?" },
  { icon: AlertTriangle, text: "¿Qué productos se me están por agotar?" },
  { icon: BarChart2,     text: "Dame un resumen del estado del inventario" },
  { icon: DollarSign,    text: "¿Cuánto capital tengo inmovilizado en stock?" },
  { icon: TrendingDown,  text: "¿Qué debería reponer con urgencia esta semana?" },
  { icon: DollarSign,    text: "¿Cuáles son mis productos de mayor valor?" },
]

const LINEAS = [
  { icon: Wrench,       label: "Lubricantes" },
  { icon: FlaskConical, label: "Químicos" },
  { icon: Flame,        label: "GLP" },
  { icon: Settings,     label: "Filtros" },
  { icon: Box,          label: "Accesorios" },
]

export default function App() {
  const [messages, setMessages]     = useState<Message[]>([])
  const [input, setInput]           = useState("")
  const [loading, setLoading]       = useState(false)
  const [sessionId, setSessionId]   = useState<string | null>(null)
  const [online, setOnline]         = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const bottomRef                   = useRef<HTMLDivElement>(null)
  const textareaRef                 = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    axios.get(`${API_URL}/health`)
      .then(() => setOnline(true))
      .catch(() => setOnline(false))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + "px"
    }
  }, [input])

  async function sendMessage(text?: string) {
    const msg = (text ?? input).trim()
    if (!msg || loading) return
    setMessages(prev => [...prev, { role: "user", content: msg, timestamp: new Date() }])
    setInput("")
    setLoading(true)
    setSidebarOpen(false)
    try {
      const res = await axios.post(`${API_URL}/chat`, { message: msg, session_id: sessionId })
      setSessionId(res.data.session_id)
      setMessages(prev => [...prev, { role: "assistant", content: res.data.response, timestamp: new Date() }])
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "⚠️ Error al conectar con el servidor.", timestamp: new Date() }])
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  function formatTime(d: Date) {
    return d.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" })
  }

  return (
    <div className="shell">
      {/* overlay mobile */}
      {sidebarOpen && <div className="overlay" onClick={() => setSidebarOpen(false)} />}

      {/* ── SIDEBAR ── */}
      <aside className={`sidebar ${sidebarOpen ? "sidebar--open" : ""}`}>
        <div className="sidebar-top">
          <img src={logo} alt="Logis" className="brand-logo" />
          <div className={`status-pill ${online ? "status-pill--online" : ""}`}>
            {online ? <Wifi size={11} /> : <WifiOff size={11} />}
            <span>{online ? "Sistema Activo" : "Sin conexión"}</span>
          </div>
        </div>

        <div className="sidebar-body">
          <div className="nav-section">
            <div className="nav-label">Consultas rápidas</div>
            {EJEMPLOS.map((e, i) => (
              <button key={i} className="nav-item" onClick={() => sendMessage(e.text)}>
                <e.icon size={13} className="nav-icon" />
                <span>{e.text}</span>
              </button>
            ))}
          </div>

          <div className="nav-section">
            <div className="nav-label">Líneas de producto</div>
            <div className="lines-list">
              {LINEAS.map(l => (
                <div key={l.label} className="line-item">
                  <l.icon size={13} />
                  <span>{l.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="sidebar-footer">
          <div className="session-info">
            <Clock size={11} />
            <span className="session-id">{sessionId ? sessionId.slice(0, 12) + "..." : "Sin sesión activa"}</span>
          </div>
          <button className="new-session-btn" onClick={() => { setMessages([]); setSessionId(null) }}>
            <RefreshCw size={12} />
            Nueva sesión
          </button>
        </div>
      </aside>

      {/* ── MAIN ── */}
      <main className="main">
        <header className="topbar">
          <div className="topbar-left">
            <button className="menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>
              {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
            <div>
              <div className="topbar-title">Asistente de Stock & Precios</div>
              <div className="topbar-sub">
                {messages.length === 0
                  ? "Listo para recibir consultas"
                  : `${messages.filter(m => m.role === "assistant").length} respuesta${messages.filter(m => m.role === "assistant").length !== 1 ? "s" : ""} en esta sesión`}
              </div>
            </div>
          </div>
        </header>

        <div className="messages">
          {messages.length === 0 ? (
            <div className="welcome">
              <div className="welcome-glow" />
              <h2 className="welcome-title">Bienvenido a Logis</h2>
              <p className="welcome-sub">
                He identificado <strong>50 productos</strong> en tu inventario. Consultame sobre stock, precios o pedime un análisis estratégico de reposición.
              </p>
              <div className="welcome-grid">
                {EJEMPLOS.slice(0, 4).map((e, i) => (
                  <button key={i} className="welcome-card" onClick={() => sendMessage(e.text)}>
                    <e.icon size={16} className="welcome-card-icon" />
                    <span>{e.text}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`msg msg--${msg.role}`}>
                <div className="msg-header">
                  <div className={`msg-avatar msg-avatar--${msg.role}`}>
                    {msg.role === "user" ? "👤" : <img src={logo} alt="Logis" className="avatar-logo" />}
                  </div>
                  <span className="msg-author">{msg.role === "user" ? "Vos" : "Logis"}</span>
                  <span className="msg-time">{formatTime(msg.timestamp)}</span>
                </div>
                <div className={`msg-bubble msg-bubble--${msg.role}`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                </div>
              </div>
            ))
          )}

          {loading && (
            <div className="msg msg--assistant">
              <div className="msg-header">
                <div className="msg-avatar msg-avatar--assistant">
                  <img src={logo} alt="Logis" className="avatar-logo" />
                </div>
                <span className="msg-author">Logis</span>
                <span className="msg-time">Consultando inventario...</span>
              </div>
              <div className="msg-bubble msg-bubble--assistant msg-bubble--loading">
                <span /><span /><span />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="input-area">
          <div className="input-wrapper">
            <textarea
              ref={textareaRef}
              className="input-box"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Preguntá sobre stock, precios o solicitá un análisis estratégico..."
              rows={1}
            />
            <div className="input-footer">
              <span className="input-hint">Enter · Shift+Enter nueva línea</span>
              <button className="send-btn" onClick={() => sendMessage()} disabled={loading || !input.trim()}>
                <Send size={14} />
                <span className="send-label">Consultar</span>
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}