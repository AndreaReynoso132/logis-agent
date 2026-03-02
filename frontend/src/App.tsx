import { useState, useRef, useEffect } from "react"
import axios from "axios"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import {
  Send, RefreshCw, Package, AlertTriangle, BarChart2,
  TrendingDown, DollarSign, Wrench, FlaskConical,
  Flame, Settings, Box, Wifi, WifiOff, Clock, Menu, X, Bot, User,
  AlertOctagon, LayoutDashboard, MessageSquare
} from "lucide-react"
import logo from "./assets/logo.png"
import "./App.css"

interface Message {
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

interface DashboardData {
  metricas: {
    total_productos: number
    agotados: number
    criticos: number
    valor_total: number
  }
  criticos_lista: {
    material: string
    cantidad: number
    minimo: number
    precio: number
    deficit: number
    estado: string
  }[]
  top_valor: {
    material: string
    cantidad: number
    precio: number
    valor_total: number
  }[]
}

const API_URL = "http://localhost:8000"

const CONSULTAS = [
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

function formatPeso(n: number) {
  return "$" + n.toLocaleString("es-AR", { maximumFractionDigits: 0 })
}

function Dashboard({ data, onRefresh, loading }: { data: DashboardData | null, onRefresh: () => void, loading: boolean }) {
  if (loading) return (
    <div className="dashboard-loading">
      <div className="dash-spinner" />
      <span>Cargando dashboard...</span>
    </div>
  )
  if (!data) return (
    <div className="dashboard-loading">
      <span>Error cargando datos.</span>
      <button className="new-session-btn" onClick={onRefresh}>Reintentar</button>
    </div>
  )

  const { metricas, criticos_lista, top_valor } = data

  return (
    <div className="dashboard">
      <div className="dash-header">
        <div>
          <div className="dash-title">Dashboard de Inventario</div>
          <div className="dash-sub">Datos en tiempo real · {new Date().toLocaleString("es-AR")}</div>
        </div>
        <button className="dash-refresh-btn" onClick={onRefresh}>
          <RefreshCw size={13} /> Actualizar
        </button>
      </div>

      <div className="dash-cards">
        <div className="dash-card">
          <div className="dash-card-icon dash-card-icon--blue"><Package size={18} /></div>
          <div className="dash-card-value">{metricas.total_productos}</div>
          <div className="dash-card-label">Total Productos</div>
        </div>
        <div className="dash-card">
          <div className="dash-card-icon dash-card-icon--red"><AlertOctagon size={18} /></div>
          <div className="dash-card-value dash-card-value--red">{metricas.agotados}</div>
          <div className="dash-card-label">Agotados</div>
        </div>
        <div className="dash-card">
          <div className="dash-card-icon dash-card-icon--yellow"><AlertTriangle size={18} /></div>
          <div className="dash-card-value dash-card-value--yellow">{metricas.criticos}</div>
          <div className="dash-card-label">Stock Crítico</div>
        </div>
        <div className="dash-card">
          <div className="dash-card-icon dash-card-icon--green"><DollarSign size={18} /></div>
          <div className="dash-card-value dash-card-value--green">{formatPeso(metricas.valor_total)}</div>
          <div className="dash-card-label">Valor Total</div>
        </div>
      </div>

      <div className="dash-tables">
        <div className="dash-table-section">
          <div className="dash-table-title">
            <AlertTriangle size={14} className="text-yellow" />
            Productos Críticos ({criticos_lista.length})
          </div>
          <div className="dash-table-wrap">
            <table className="dash-table">
              <thead>
                <tr>
                  <th>Estado</th>
                  <th>Producto</th>
                  <th>Stock</th>
                  <th>Mín.</th>
                  <th>Déficit</th>
                </tr>
              </thead>
              <tbody>
                {criticos_lista.length === 0 ? (
                  <tr><td colSpan={5} className="dash-empty">✅ Sin productos críticos</td></tr>
                ) : criticos_lista.map((p, i) => (
                  <tr key={i}>
                    <td>
                      <span className={`dash-badge ${p.estado === "agotado" ? "dash-badge--red" : "dash-badge--yellow"}`}>
                        {p.estado === "agotado" ? "🔴 Agotado" : "🟡 Bajo"}
                      </span>
                    </td>
                    <td className="dash-material">{p.material}</td>
                    <td className="dash-num">{p.cantidad}</td>
                    <td className="dash-num">{p.minimo}</td>
                    <td className="dash-num dash-deficit">-{p.deficit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="dash-table-section">
          <div className="dash-table-title">
            <DollarSign size={14} className="text-accent" />
            Top 5 por Valor
          </div>
          <div className="dash-table-wrap">
            <table className="dash-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Producto</th>
                  <th>Stock</th>
                  <th>Valor Total</th>
                </tr>
              </thead>
              <tbody>
                {top_valor.map((p, i) => (
                  <tr key={i}>
                    <td className="dash-num dash-rank">#{i + 1}</td>
                    <td className="dash-material">{p.material}</td>
                    <td className="dash-num">{p.cantidad}</td>
                    <td className="dash-num dash-valor">{formatPeso(p.valor_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [messages, setMessages]           = useState<Message[]>([])
  const [input, setInput]                 = useState("")
  const [loading, setLoading]             = useState(false)
  const [sessionId, setSessionId]         = useState<string | null>(null)
  const [online, setOnline]               = useState(false)
  const [totalProductos, setTotalProductos] = useState<number>(0)
  const [sidebarOpen, setSidebarOpen]     = useState(false)
  const [view, setView]                   = useState<"chat" | "dashboard">("chat")
  const [dashData, setDashData]           = useState<DashboardData | null>(null)
  const [dashLoading, setDashLoading]     = useState(false)
  const bottomRef                         = useRef<HTMLDivElement>(null)
  const textareaRef                       = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    axios.get(`${API_URL}/health`)
      .then(res => {
        setOnline(true)
        setTotalProductos(res.data.productos ?? 0)
      })
      .catch(() => setOnline(false))
  }, [])

  useEffect(() => {
    if (view === "dashboard") loadDashboard()
  }, [view])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + "px"
    }
  }, [input])

  async function loadDashboard() {
    setDashLoading(true)
    try {
      const res = await axios.get(`${API_URL}/dashboard`)
      setDashData(res.data)
    } catch {
      setDashData(null)
    } finally {
      setDashLoading(false)
    }
  }

  async function sendMessage(text?: string) {
    const msg = (text ?? input).trim()
    if (!msg || loading) return
    setView("chat")
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
      {sidebarOpen && <div className="overlay" onClick={() => setSidebarOpen(false)} />}

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
            {CONSULTAS.map((e, i) => (
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

      <main className="main">
        <header className="topbar">
          <div className="topbar-left">
            <button className="menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>
              {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
            <div>
              <div className="topbar-title">Asistente de Stock & Precios</div>
              <div className="topbar-sub">
                {view === "dashboard"
                  ? "Vista de Dashboard"
                  : messages.length === 0
                    ? "Listo para recibir consultas"
                    : `${messages.filter(m => m.role === "assistant").length} respuesta${messages.filter(m => m.role === "assistant").length !== 1 ? "s" : ""} en esta sesión`}
              </div>
            </div>
          </div>
          <div className="topbar-right">
            <div className="view-toggle">
              <button className={`view-btn ${view === "chat" ? "view-btn--active" : ""}`} onClick={() => setView("chat")}>
                <MessageSquare size={13} /> <span className="view-btn-label">Chat</span>
              </button>
              <button className={`view-btn ${view === "dashboard" ? "view-btn--active" : ""}`} onClick={() => setView("dashboard")}>
                <LayoutDashboard size={13} /> <span className="view-btn-label">Dashboard</span>
              </button>
            </div>
          </div>
        </header>

        {view === "dashboard" ? (
          <Dashboard data={dashData} onRefresh={loadDashboard} loading={dashLoading} />
        ) : (
          <>
            <div className="messages">
              {messages.length === 0 ? (
                <div className="welcome">
                  <div className="welcome-glow" />
                  <h2 className="welcome-title">Bienvenido a Logis</h2>
                  <p className="welcome-sub">
                    He identificado <strong>{totalProductos} productos</strong> en tu inventario. Consultame sobre stock, precios o pedime un análisis estratégico.
                  </p>
                  <div className="welcome-grid">
                    {CONSULTAS.slice(0, 4).map((e, i) => (
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
                        {msg.role === "user"
                          ? <User size={14} className="avatar-icon avatar-icon--user" />
                          : <Bot  size={14} className="avatar-icon avatar-icon--bot" />}
                      </div>
                      <span className="msg-author">{msg.role === "user" ? "Analista" : "Logis"}</span>
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
                      <Bot size={14} className="avatar-icon avatar-icon--bot" />
                    </div>
                    <span className="msg-author">Logis</span>
                    <span className="msg-time">Procesando consulta...</span>
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
          </>
        )}
      </main>
    </div>
  )
}