import React, { useEffect, useState } from 'react'
import { api, fen2yuan, yuan2fen } from '../api.js'
import MarketplaceIcon from '../components/MarketplaceIcon.jsx'

export default function SettingsPage() {
  const [form, setForm] = useState(null)
  const [marketplaces, setMarketplaces] = useState([])
  const [marketForm, setMarketForm] = useState({ name: '', icon_path: '' })
  const [editingMarket, setEditingMarket] = useState(null)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [uploading, setUploading] = useState(false)

  function loadMarketplaces() { api.listMarketplaces().then(setMarketplaces).catch((e) => setError(e.message)) }
  useEffect(() => {
    api.getSettings().then((data) => setForm({ threshold: fen2yuan(data.alipay_fee_threshold_fen), rate: String(data.alipay_fee_rate * 100), fx: String(data.fx_cny_eur), fx_mode: data.fx_mode || 'historical', display_currency: data.display_currency || 'EUR', inventory_page_size: String(data.inventory_page_size || 20) })).catch((e) => setError(e.message))
    loadMarketplaces()
  }, [])

  async function save() {
    setSaving(true); setSaved(false); setError(null)
    try {
      const data = await api.updateSettings({ alipay_fee_threshold_fen: yuan2fen(form.threshold), alipay_fee_rate: (parseFloat(form.rate) || 0) / 100, fx_cny_eur: parseFloat(form.fx) || 0, fx_mode: form.fx_mode, display_currency: form.display_currency, inventory_page_size: parseInt(form.inventory_page_size, 10) || 20 })
      setForm({ threshold: fen2yuan(data.alipay_fee_threshold_fen), rate: String(data.alipay_fee_rate * 100), fx: String(data.fx_cny_eur), fx_mode: data.fx_mode, display_currency: data.display_currency, inventory_page_size: String(data.inventory_page_size) }); setSaved(true)
    } catch (e) { setError(e.message) } finally { setSaving(false) }
  }

  async function selectIcon(file) {
    if (!file) return
    setUploading(true); setError(null)
    try { const uploaded = await api.uploadImage({ filename: file.name, data: await readBase64(file) }); setMarketForm((current) => ({ ...current, icon_path: uploaded.image_path })) }
    catch (e) { setError(e.message) } finally { setUploading(false) }
  }

  async function addMarketplace() {
    if (!marketForm.name.trim()) return setError('Indica el nombre del marketplace.')
    setError(null)
    try { await api.createMarketplace({ name: marketForm.name, icon_path: marketForm.icon_path || null }); setMarketForm({ name: '', icon_path: '' }); loadMarketplaces() }
    catch (e) { setError(e.message) }
  }

  async function removeMarketplace(market) {
    setError(null)
    try { await api.deleteMarketplace(market.code); if (editingMarket?.code === market.code) setEditingMarket(null); loadMarketplaces() } catch (e) { setError(e.message) }
  }

  async function saveMarketplaceEdit() {
    if (!editingMarket.name.trim()) return setError('Indica el nombre del marketplace.')
    setError(null)
    try {
      await api.updateMarketplace(editingMarket.code, { name: editingMarket.name, icon_path: editingMarket.icon_path || null })
      setEditingMarket(null); loadMarketplaces()
    } catch (e) { setError(e.message) }
  }

  async function selectEditIcon(file) {
    if (!file) return
    setUploading(true); setError(null)
    try { const uploaded = await api.uploadImage({ filename: file.name, data: await readBase64(file) }); setEditingMarket((current) => ({ ...current, icon_path: uploaded.image_path })) }
    catch (e) { setError(e.message) } finally { setUploading(false) }
  }

  if (!form) return error ? <div className="err">{error}</div> : <div className="muted">Cargando…</div>
  return <div className="settings-page">
    <div className="settings-heading"><div><h1>Ajustes</h1><p className="muted">Configura cómo se calculan y muestran los costes de la aplicación.</p></div><button onClick={save} disabled={saving}>{saving ? 'Guardando…' : 'Guardar cambios'}</button></div>
    {error && <div className="err">{error}</div>}{saved && <div className="ok">Ajustes guardados ✓</div>}

    <SettingsSection icon="€" title="Moneda y conversión" description="Define el tipo de cambio y la moneda principal de la interfaz.">
      <div className="settings-grid">
        <Field label="Conversión CNY → EUR" help={form.fx_mode === 'historical' ? 'Se aplica el cambio oficial del día de compra.' : 'Se aplica la misma tasa a las órdenes nuevas.'}><select value={form.fx_mode} onChange={(e) => setForm({ ...form, fx_mode: e.target.value })}><option value="historical">Tipo de cambio del día de compra</option><option value="fixed">Tasa fija</option></select></Field>
        {form.fx_mode === 'fixed' && <Field label="Tasa fija CNY → EUR"><input value={form.fx} onChange={(e) => setForm({ ...form, fx: e.target.value })} /></Field>}
        <Field label="Moneda de visualización" help="El equivalente en euros seguirá visible como referencia."><select value={form.display_currency} onChange={(e) => setForm({ ...form, display_currency: e.target.value })}><option value="EUR">Euro (€)</option><option value="CNY">Yuan (¥)</option></select></Field>
      </div>
    </SettingsSection>

    <SettingsSection icon="%" title="Comisiones de compra" description="Reglas utilizadas para calcular automáticamente los gastos de Alipay.">
      <div className="settings-grid"><Field label="Umbral de comisión Alipay (¥)" help="La comisión se aplica cuando la compra supera este importe."><input value={form.threshold} onChange={(e) => setForm({ ...form, threshold: e.target.value })} /></Field><Field label="Tasa Alipay (%)" help="Porcentaje añadido al coste de la compra."><input value={form.rate} onChange={(e) => setForm({ ...form, rate: e.target.value })} /></Field></div>
    </SettingsSection>

    <SettingsSection icon="20" title="Inventario" description="Configura cuántas cartas aparecen en cada página del inventario.">
      <div className="settings-grid">
        <Field label="Cartas por página" help="Puedes elegir entre 1 y 200 cartas.">
          <input type="number" min="1" max="200" value={form.inventory_page_size} onChange={(e) => setForm({ ...form, inventory_page_size: e.target.value })} />
        </Field>
      </div>
    </SettingsSection>

    <SettingsSection icon="M" title="Marketplaces" description="Gestiona los canales disponibles al publicar y editar anuncios.">
      <div className="marketplace-settings-list">{marketplaces.map((market) => <div className="marketplace-settings-row" key={market.code}><MarketplaceIcon marketplace={market.code} iconPath={market.icon_path} name={market.name} /><div><strong>{market.name}</strong><small>{market.builtin ? 'Marketplace preconfigurado' : 'Marketplace personalizado'}</small></div><div className="marketplace-row-actions"><button className="secondary" onClick={() => setEditingMarket({ ...market })}>Editar</button><button className="secondary danger-button" onClick={() => removeMarketplace(market)}>Eliminar</button></div></div>)}</div>
      <div className="marketplace-add-panel"><h3>Añadir marketplace</h3><div className="marketplace-add-form">
        <div className="marketplace-icon-preview">{marketForm.icon_path ? <img src={`/images/${marketForm.icon_path}`} alt="Vista previa" /> : <span>Icono</span>}<label>{uploading ? 'Subiendo…' : 'Elegir imagen'}<input type="file" accept="image/*" disabled={uploading} onChange={(e) => selectIcon(e.target.files?.[0])} /></label></div>
        <Field label="Nombre"><input value={marketForm.name} onChange={(e) => setMarketForm({ ...marketForm, name: e.target.value })} placeholder="Por ejemplo, TCGplayer" /></Field><button onClick={addMarketplace}>Añadir marketplace</button>
      </div></div>
      {editingMarket && <div className="marketplace-edit-panel"><div className="marketplace-edit-heading"><h3>Editar marketplace</h3><button className="secondary" onClick={() => setEditingMarket(null)}>Cancelar</button></div><div className="marketplace-add-form">
        <div className="marketplace-icon-preview">{editingMarket.icon_path ? <img src={`/images/${editingMarket.icon_path}`} alt="Vista previa" /> : <span>Icono</span>}<label>{uploading ? 'Subiendo…' : 'Cambiar imagen'}<input type="file" accept="image/*" disabled={uploading} onChange={(e) => selectEditIcon(e.target.files?.[0])} /></label></div>
        <Field label="Nombre"><input value={editingMarket.name} onChange={(e) => setEditingMarket({ ...editingMarket, name: e.target.value })} /></Field><button onClick={saveMarketplaceEdit}>Guardar cambios</button>
      </div></div>}
    </SettingsSection>
  </div>
}

function SettingsSection({ icon, title, description, children }) { return <section className="card settings-section"><div className="settings-section-title"><span className="settings-section-icon">{icon}</span><div><h2>{title}</h2><p>{description}</p></div></div>{children}</section> }
function Field({ label, help, children }) { return <div className="field"><label>{label}</label>{children}{help && <small>{help}</small>}</div> }
function readBase64(file) { return new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result).split(',')[1]); reader.onerror = () => reject(new Error('No se pudo leer la imagen')); reader.readAsDataURL(file) }) }
