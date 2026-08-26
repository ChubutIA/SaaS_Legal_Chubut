import { apiGetIpc } from './api.js';

let ipcData = [];
const mesesNombres = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

export const IpcCalculator = {
  async init() {
    await this.fetchIndices();
    this.populateSelects();
    this.bindEvents();
  },

  async fetchIndices() {
    try {
      // Le pedimos los datos a tu backend en Python
      const data = await apiGetIpc();
      ipcData = data;
    } catch (error) {
      console.error("Error al cargar índices IPC:", error);
    }
  },

  populateSelects() {
    if (!ipcData.length) return;

    // Extraer años únicos para los desplegables
    const anios = [...new Set(ipcData.map(d => d.anio))];
    
    const selectAnioInicio = document.getElementById('ipc-anio-inicio');
    const selectAnioFin = document.getElementById('ipc-anio-fin');
    
    selectAnioInicio.innerHTML = '';
    selectAnioFin.innerHTML = '';

    anios.forEach(anio => {
      selectAnioInicio.innerHTML += `<option value="${anio}">${anio}</option>`;
      selectAnioFin.innerHTML += `<option value="${anio}">${anio}</option>`;
    });

    // Setear por defecto el año más viejo al inicio y el más nuevo al final
    selectAnioInicio.value = anios[0];
    selectAnioFin.value = anios[anios.length - 1];

    this.updateMonths('inicio');
    this.updateMonths('fin');

    // Setear el mes más reciente disponible por defecto en el campo "Fin" (ej: Julio 2026)
    const mesesFin = ipcData.filter(d => d.anio == selectAnioFin.value);
    if(mesesFin.length > 0) {
        document.getElementById('ipc-mes-fin').value = mesesFin[mesesFin.length - 1].mes;
    }
  },

  updateMonths(type) {
    const selectAnio = document.getElementById(`ipc-anio-${type}`);
    const selectMes = document.getElementById(`ipc-mes-${type}`);
    const anioSeleccionado = parseInt(selectAnio.value);

    // Buscar qué meses tenemos guardados para el año seleccionado (ej: 2016 solo tiene Diciembre)
    const mesesDisponibles = ipcData.filter(d => d.anio === anioSeleccionado);
    const mesPrevio = selectMes.value;

    selectMes.innerHTML = '';
    mesesDisponibles.forEach(d => {
      selectMes.innerHTML += `<option value="${d.mes}">${mesesNombres[d.mes]}</option>`;
    });

    // Intentar mantener el mes que estaba seleccionado si sigue disponible
    if (mesPrevio && mesesDisponibles.some(d => d.mes == mesPrevio)) {
      selectMes.value = mesPrevio;
    }
  },

  bindEvents() {
    // Actualizar los meses disponibles cuando el usuario cambia el año
    document.getElementById('ipc-anio-inicio')?.addEventListener('change', () => this.updateMonths('inicio'));
    document.getElementById('ipc-anio-fin')?.addEventListener('change', () => this.updateMonths('fin'));

    // Manejar el clic en el botón de calcular
    document.getElementById('ipc-form')?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.calcular();
    });
  },

  calcular() {
    const monto = parseFloat(document.getElementById('ipc-monto').value);
    const anioInicio = parseInt(document.getElementById('ipc-anio-inicio').value);
    const mesInicio = parseInt(document.getElementById('ipc-mes-inicio').value);
    const anioFin = parseInt(document.getElementById('ipc-anio-fin').value);
    const mesFin = parseInt(document.getElementById('ipc-mes-fin').value);

    // Buscar los índices exactos en nuestra base de datos en memoria
    const datoInicio = ipcData.find(d => d.anio === anioInicio && d.mes === mesInicio);
    const datoFin = ipcData.find(d => d.anio === anioFin && d.mes === mesFin);

    if (!datoInicio || !datoFin) {
      alert("Error: Faltan datos de inflación para el período seleccionado.");
      return;
    }

    const indiceInicio = parseFloat(datoInicio.indice);
    const indiceFin = parseFloat(datoFin.indice);
    
    // La fórmula matemática exacta del INDEC:
    const coeficiente = indiceFin / indiceInicio;
    const montoActualizado = monto * coeficiente;

    // Actualizar los textos en pantalla
    document.getElementById('ipc-idx-inicio').innerText = indiceInicio.toFixed(4);
    document.getElementById('ipc-idx-fin').innerText = indiceFin.toFixed(4);
    document.getElementById('ipc-coef').innerText = coeficiente.toFixed(4);
    
    const formatoMoneda = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' });
    document.getElementById('ipc-monto-res').innerText = formatoMoneda.format(montoActualizado);
    document.getElementById('ipc-fecha-res').innerText = `${mesesNombres[mesFin]} de ${anioFin}`;
    
    // Mostrar la caja de resultados con animación
    document.getElementById('ipc-resultado').classList.remove('hidden');
  }
};
