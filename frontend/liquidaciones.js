/**
 * liquidaciones.js
 * Módulo de la vista "Liquidaciones" (estilo SICAL) para Chubut.IA.
 *
 * Patrón: módulo ES6 con estado privado + API pública mínima (init/destroy).
 * No depende de frameworks. Se integra con el router de tu SPA llamando
 * a Liquidaciones.init() cuando la vista #view-liquidaciones se monta,
 * y opcionalmente Liquidaciones.destroy() al desmontarla.
 *
 * Uso típico en tu router:
 *   import { Liquidaciones } from './liquidaciones.js';
 *   ...
 *   case 'liquidaciones':
 *     contenedor.innerHTML = await fetch('/views/liquidaciones.html').then(r => r.text());
 *     Liquidaciones.init();
 *     break;
 */

// -----------------------------------------------------------------------
// Config — ajustá según tus endpoints reales de FastAPI
// -----------------------------------------------------------------------
const API_BASE = '/api';
const ENDPOINTS = {
  canastaValor: `${API_BASE}/canasta-basica/valor`, // GET ?mes_anio=&tramo_edad=
  tasaInteres: `${API_BASE}/intereses/calcular`,      // POST { monto, tasa, desde, hasta }
};

const CONCEPTOS_LABEL = {
  capital: 'Capital',
  canasta_basica_crianza: 'Canasta Básica de Crianza',
  honorarios: 'Honorarios',
  otros: 'Otros',
};

export const Liquidaciones = (() => {
  // ---------------------------------------------------------------------
  // Estado privado del módulo
  // ---------------------------------------------------------------------
  let items = [];        // { id, concepto, conceptoLabel, detalle, importe, meta, selected }
  let nextId = 1;
  let els = {};           // cache de elementos del DOM
  let mounted = false;

  // ---------------------------------------------------------------------
  // Utilidades
  // ---------------------------------------------------------------------
  function formatMoney(value) {
    const n = Number(value) || 0;
    return n.toLocaleString('es-AR', {
      style: 'currency',
      currency: 'ARS',
      minimumFractionDigits: 2,
    });
  }

  function qs(id) {
    return document.getElementById(id);
  }

  function cacheEls() {
    els = {
      form: qs('liq-form'),
      concepto: qs('liq-concepto'),
      canastaFields: qs('liq-canasta-fields'),
      mesAnio: qs('liq-mes-anio'),
      tramoEdad: qs('liq-tramo-edad'),
      detalle: qs('liq-detalle'),
      importe: qs('liq-importe'),
      btnAgregar: qs('btn-agregar-item'),

      tablaBody: qs('tabla-liquidacion-body'),
      filaVacia: qs('tabla-liquidacion-empty'),
      total: qs('liq-total'),

      btnTotalizar: qs('btn-totalizar'),
      btnInteres: qs('btn-interes'),
      btnImprimir: qs('btn-imprimir'),
      btnLimpiar: qs('btn-limpiar'),

      calculoIntereses: qs('calculo-intereses'),
      intMonto: qs('int-monto'),
      intTasa: qs('int-tasa'),
      intDesde: qs('int-desde'),
      intHasta: qs('int-hasta'),
      btnAplicarInteres: qs('btn-aplicar-interes'),
      intResultado: qs('int-resultado'),
    };
  }

  // ---------------------------------------------------------------------
  // Poblado de selects dinámicos
  // ---------------------------------------------------------------------
  function poblarMesAnio() {
    // Genera los últimos 36 meses (ajustá el rango a lo que necesite tu sistema)
    const meses = [
      'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
      'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
    ];
    const hoy = new Date();
    const opciones = [];

    for (let i = 0; i < 80; i++) {
      const d = new Date(hoy.getFullYear(), hoy.getMonth() - i, 1);
      const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      const label = `${meses[d.getMonth()]} ${d.getFullYear()}`;
      opciones.push({ value, label });
    }

    els.mesAnio.innerHTML = opciones
      .map((o) => `<option value="${o.value}">${o.label}</option>`)
      .join('');
  }

  // ---------------------------------------------------------------------
  // Manejo de "Concepto" -> mostrar/ocultar campos de Canasta Básica
  // ---------------------------------------------------------------------
  function onConceptoChange() {
    const esCanasta = els.concepto.value === 'canasta_basica_crianza';

    els.canastaFields.classList.toggle('hidden', !esCanasta);

    if (esCanasta) {
      els.importe.readOnly = true;
      els.importe.value = '';
      els.importe.placeholder = 'Se completa automáticamente';
      actualizarImporteCanasta();
    } else {
      els.importe.readOnly = false;
      els.importe.placeholder = '0.00';
      els.importe.value = '';
    }
  }

  // Trae el valor de la canasta básica desde el backend según Mes/Año + Tramo
  async function actualizarImporteCanasta() {
    const mesAnio = els.mesAnio.value;
    const tramoEdad = els.tramoEdad.value;
    if (!mesAnio || !tramoEdad) return;

    try {
      els.importe.value = '';
      els.importe.placeholder = 'Consultando...';

      const url = `${ENDPOINTS.canastaValor}?mes_anio=${encodeURIComponent(mesAnio)}&tramo_edad=${encodeURIComponent(tramoEdad)}`;
      const resp = await fetch(url, { credentials: 'include' });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      // Ajustá esta clave al shape real que devuelva tu endpoint
      els.importe.value = Number(data.importe ?? 0).toFixed(2);
    } catch (err) {
      console.error('[Liquidaciones] Error al obtener valor de canasta básica:', err);
      els.importe.value = '';
      els.importe.placeholder = 'No se pudo obtener el valor';
    }
  }

  // ---------------------------------------------------------------------
  // Alta de item
  // ---------------------------------------------------------------------
  function onSubmitForm(e) {
    e.preventDefault();

    const conceptoValue = els.concepto.value;
    if (!conceptoValue) {
      els.concepto.focus();
      return;
    }

    const importe = parseFloat(els.importe.value);
    if (isNaN(importe) || importe <= 0) {
      els.importe.focus();
      return;
    }

    let conceptoLabel = CONCEPTOS_LABEL[conceptoValue] || conceptoValue;
    let meta = null;

    if (conceptoValue === 'canasta_basica_crianza') {
      const mesAnioLabel = els.mesAnio.selectedOptions[0]?.textContent ?? '';
      const tramoLabel = els.tramoEdad.selectedOptions[0]?.dataset.label
        ?? els.tramoEdad.selectedOptions[0]?.textContent
        ?? '';
      meta = { mesAnio: els.mesAnio.value, tramoEdad: els.tramoEdad.value };
      conceptoLabel = `${conceptoLabel} (${mesAnioLabel} · ${tramoLabel})`;
    }

    const item = {
      id: nextId++,
      concepto: conceptoValue,
      conceptoLabel,
      detalle: els.detalle.value.trim(),
      importe,
      meta,
      selected: false,
    };

    items.push(item);
    render();
    resetForm();
  }

  function resetForm() {
    els.form.reset();
    els.canastaFields.classList.add('hidden');
    els.importe.readOnly = false;
    els.importe.placeholder = '0.00';
  }

  // ---------------------------------------------------------------------
  // Eliminar item / selección de checkboxes (delegación de eventos)
  // ---------------------------------------------------------------------
  function onTablaClick(e) {
    const btnEliminar = e.target.closest('[data-action="eliminar"]');
    if (btnEliminar) {
      const id = Number(btnEliminar.dataset.id);
      items = items.filter((it) => it.id !== id);
      render();
      return;
    }
  }

  function onTablaChange(e) {
    const checkbox = e.target.closest('[data-action="seleccionar"]');
    if (checkbox) {
      const id = Number(checkbox.dataset.id);
      const item = items.find((it) => it.id === id);
      if (item) item.selected = checkbox.checked;
      actualizarMontoIntereses();
    }
  }

  // ---------------------------------------------------------------------
  // Render de la tabla y totales
  // ---------------------------------------------------------------------
  function render() {
    if (items.length === 0) {
      els.tablaBody.innerHTML = '';
      els.tablaBody.appendChild(els.filaVacia);
      els.filaVacia.classList.remove('hidden');
    } else {
      els.filaVacia.classList.add('hidden');
      els.tablaBody.innerHTML = items
        .map(
          (item, idx) => `
        <tr data-id="${item.id}">
          <td>${idx + 1}</td>
          <td>${escapeHtml(item.conceptoLabel)}${item.detalle ? ` — ${escapeHtml(item.detalle)}` : ''}</td>
          <td>${formatMoney(item.importe)}</td>
          <td class="text-center">
            <input type="checkbox" data-action="seleccionar" data-id="${item.id}" ${item.selected ? 'checked' : ''}>
          </td>
          <td class="text-center">
            <button type="button" class="btn btn-sm btn-danger" data-action="eliminar" data-id="${item.id}">
              Eliminar
            </button>
          </td>
        </tr>`
        )
        .join('');
    }

    actualizarTotal();
    actualizarMontoIntereses();
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str ?? '';
    return div.innerHTML;
  }

  function actualizarTotal() {
    const total = items.reduce((acc, it) => acc + it.importe, 0);
    els.total.innerHTML = `<strong>${formatMoney(total)}</strong>`;
    return total;
  }

  // ---------------------------------------------------------------------
  // Botón "+ TOTALIZAR" — recalcula y resalta el total (misma lógica que
  // actualizarTotal, expuesto como acción explícita para el usuario)
  // ---------------------------------------------------------------------
  function onTotalizar() {
    const total = actualizarTotal();
    els.total.classList.add('total-flash');
    setTimeout(() => els.total.classList.remove('total-flash'), 600);
    return total;
  }

  // ---------------------------------------------------------------------
  // Botón "LIMPIAR LIQUIDACIÓN"
  // ---------------------------------------------------------------------
  function onLimpiar() {
    if (items.length > 0) {
      const confirmar = window.confirm('¿Seguro que querés limpiar toda la liquidación? Esta acción no se puede deshacer.');
      if (!confirmar) return;
    }
    items = [];
    nextId = 1;
    render();
    resetForm();
    els.calculoIntereses.classList.add('hidden');
    els.intResultado.classList.add('hidden');
  }

  // ---------------------------------------------------------------------
  // Sección de Cálculo de Intereses
  // ---------------------------------------------------------------------
  function onToggleInteres() {
    els.calculoIntereses.classList.toggle('hidden');
    if (!els.calculoIntereses.classList.contains('hidden')) {
      actualizarMontoIntereses();
      els.calculoIntereses.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function actualizarMontoIntereses() {
    const seleccionados = items.filter((it) => it.selected);
    const monto = seleccionados.reduce((acc, it) => acc + it.importe, 0);
    els.intMonto.value = seleccionados.length > 0 ? formatMoney(monto) : '';
    return monto;
  }

  async function onAplicarInteres() {
    const seleccionados = items.filter((it) => it.selected);
    if (seleccionados.length === 0) {
      alert('Seleccioná al menos un ítem de la tabla para calcular intereses.');
      return;
    }

    const monto = seleccionados.reduce((acc, it) => acc + it.importe, 0);
    const tasa = els.intTasa.value;
    const desde = els.intDesde.value;
    const hasta = els.intHasta.value;

    if (!desde || !hasta) {
      alert('Completá Fecha Desde y Fecha Hasta.');
      return;
    }
    if (new Date(desde) > new Date(hasta)) {
      alert('La Fecha Desde no puede ser posterior a la Fecha Hasta.');
      return;
    }

    els.btnAplicarInteres.disabled = true;
    els.btnAplicarInteres.textContent = 'Calculando...';

    try {
      const resp = await fetch(ENDPOINTS.tasaInteres, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ monto, tasa, desde, hasta }),
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      // Ajustá las claves al shape real de tu respuesta FastAPI
      mostrarResultadoInteres({
        montoBase: monto,
        interes: data.interes ?? 0,
        montoTotal: data.monto_total ?? monto + (data.interes ?? 0),
        tasaLabel: els.intTasa.selectedOptions[0]?.textContent ?? tasa,
      });
    } catch (err) {
      console.error('[Liquidaciones] Error al calcular intereses:', err);
      alert('No se pudo calcular el interés. Intentá nuevamente.');
    } finally {
      els.btnAplicarInteres.disabled = false;
      els.btnAplicarInteres.textContent = 'APLICAR';
    }
  }

  function mostrarResultadoInteres({ montoBase, interes, montoTotal, tasaLabel }) {
    els.intResultado.innerHTML = `
      <p><strong>Tasa aplicada:</strong> ${escapeHtml(tasaLabel)}</p>
      <p><strong>Monto base:</strong> ${formatMoney(montoBase)}</p>
      <p><strong>Interés calculado:</strong> ${formatMoney(interes)}</p>
      <p><strong>Monto total actualizado:</strong> ${formatMoney(montoTotal)}</p>
    `;
    els.intResultado.classList.remove('hidden');
  }

  // ---------------------------------------------------------------------
  // Imprimir
  // ---------------------------------------------------------------------
  function onImprimir() {
    window.print();
    // Alternativa si necesitás un layout de impresión distinto al de pantalla:
    // generar un HTML con los `items` y abrirlo en una nueva ventana / iframe.
  }

  // ---------------------------------------------------------------------
  // Ciclo de vida del módulo
  // ---------------------------------------------------------------------
  function bindEvents() {
    els.concepto.addEventListener('change', onConceptoChange);
    els.mesAnio.addEventListener('change', actualizarImporteCanasta);
    els.tramoEdad.addEventListener('change', actualizarImporteCanasta);
    els.form.addEventListener('submit', onSubmitForm);

    els.tablaBody.addEventListener('click', onTablaClick);
    els.tablaBody.addEventListener('change', onTablaChange);

    els.btnTotalizar.addEventListener('click', onTotalizar);
    els.btnInteres.addEventListener('click', onToggleInteres);
    els.btnImprimir.addEventListener('click', onImprimir);
    els.btnLimpiar.addEventListener('click', onLimpiar);

    els.btnAplicarInteres.addEventListener('click', onAplicarInteres);
  }

  function unbindEvents() {
    els.concepto.removeEventListener('change', onConceptoChange);
    els.mesAnio.removeEventListener('change', actualizarImporteCanasta);
    els.tramoEdad.removeEventListener('change', actualizarImporteCanasta);
    els.form.removeEventListener('submit', onSubmitForm);

    els.tablaBody.removeEventListener('click', onTablaClick);
    els.tablaBody.removeEventListener('change', onTablaChange);

    els.btnTotalizar.removeEventListener('click', onTotalizar);
    els.btnInteres.removeEventListener('click', onToggleInteres);
    els.btnImprimir.removeEventListener('click', onImprimir);
    els.btnLimpiar.removeEventListener('click', onLimpiar);

    els.btnAplicarInteres.removeEventListener('click', onAplicarInteres);
  }

  function init() {
    if (mounted) destroy(); // evita doble binding si el router re-monta la vista

    cacheEls();
    if (!els.form) {
      console.error('[Liquidaciones] No se encontró #liq-form en el DOM. ¿Se inyectó liquidaciones.html?');
      return;
    }

    poblarMesAnio();
    bindEvents();
    render();

    mounted = true;
  }

  function destroy() {
    if (!mounted) return;
    unbindEvents();
    items = [];
    nextId = 1;
    mounted = false;
  }

  // API pública del módulo
  return {
    init,
    destroy,
    // expuestos por si el router/tests necesitan inspeccionar estado
    getItems: () => [...items],
    getTotal: () => items.reduce((acc, it) => acc + it.importe, 0),
  };
})();
