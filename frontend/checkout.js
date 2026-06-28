import { state } from './state.js';
import { processPayment } from './api.js';
import { openCheckoutModal, closeCheckoutModal, showPaymentResult, showToast, showModal } from './ui.js';

// Tu clave pública de Mercado Pago (¡Asegurate de usar la de PRUEBA que empieza con TEST-!)
const MP_PUBLIC_KEY = 'APP_USR-58c1aa93-295b-4b5d-bb13-4de93f6b784e'; 
const PLAN_PRO_AMOUNT = 6500;

let brickController = null;

// Nueva función para pedirle al backend el ID de preferencia
async function getPreferenceId() {
  // Ajustá los headers según cómo manejes la autenticación (Bearer token de Supabase)
  const token = localStorage.getItem('sb-tu_proyecto-auth-token'); // Cambiá esto si guardás el token con otro nombre
  
  // Usá la ruta completa si es necesario, ej: https://tu-railway-app.up.railway.app/api/payments/create-preference
  const res = await fetch('/api/payments/create-preference', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      // Si usás cookies para auth, la siguiente línea no hace falta. 
      // Si usás token JWT, asegurate de mandarlo acá:
      // 'Authorization': `Bearer ${token}` 
    },
    credentials: 'include' 
  });

  if (!res.ok) {
    throw new Error('No se pudo crear la preferencia de pago');
  }
  
  const data = await res.json();
  return data.preference_id;
}

export async function initPaymentBrick() {
  if (brickController) {
    await brickController.unmount();
    brickController = null;
  }

  const resultDiv = document.getElementById('payment-result');
  if (resultDiv) resultDiv.classList.add('hidden');

  const container = document.getElementById('payment-brick-container');
  if (container) {
    container.style.display = 'block';
    container.innerHTML = 'Cargando opciones de pago...';
  }

  // 1. Obtenemos el preferenceId ANTES de inicializar
  let preferenceId;
  try {
    preferenceId = await getPreferenceId();
  } catch (error) {
    console.error(error);
    if (container) container.innerHTML = 'Error al cargar el pago. Intentá de nuevo.';
    return;
  }

  const mp = new MercadoPago(MP_PUBLIC_KEY, { locale: 'es-AR' });
  const bricksBuilder = mp.bricks();

  const settings = {
    initialization: {
      amount: PLAN_PRO_AMOUNT,
      preferenceId: preferenceId, // <--- ¡ACÁ ESTÁ LA MAGIA!
    },
    customization: {
      visual: {
        style: {
          theme: 'dark',
          customVariables: {
            baseColor: '#c9a84c',
          }
        }
      },
      paymentMethods: {
        creditCard: 'all',
        debitCard: 'all',
        mercadoPago: 'all' // Ahora sí se va a mostrar
      }
    },
    callbacks: {
      onReady: () => {
        console.log('Brick Renderizado exitosamente');
      },
      onSubmit: ({ selectedPaymentMethod, formData }) => {
        // SI PAGA CON BILLETERA:
        if (selectedPaymentMethod === 'wallet_purchase') {
          // El SDK de Mercado Pago lo redirige automáticamente.
          // No procesamos nada manual acá, solo cerramos la promesa.
          return new Promise((resolve) => resolve());
        }

        // SI PAGA CON TARJETA:
        return new Promise((resolve, reject) => {
          processPayment(formData)
            .then((result) => {
              if (result.status === 'approved') {
                resolve();
                showPaymentResult('approved', result.message);
              } else if (result.status === 'pending' || result.status === 'in_process') {
                resolve();
                showPaymentResult('pending', result.message);
              } else {
                reject(new Error(result.message));
              }
            })
            .catch((error) => {
              reject(new Error(error.message || 'No se pudo procesar el pago.'));
            });
        });
      },
      onError: (error) => {
        console.error('Error en el Brick:', error);
      }
    }
  };

  try {
    brickController = await bricksBuilder.create('payment', 'payment-brick-container', settings);
  } catch (err) {
    console.error("Fallo crítico al crear el Brick:", err);
  }
}

export function setupCheckoutListeners() {
  document.body.addEventListener('click', async (e) => {
    
    const btnOpen = e.target.closest('#btn-open-checkout');
    if (btnOpen) {
      if (!state.user || !state.user.email) {
        showToast('Tenés que iniciar sesión o registrarte para suscribirte al Plan Pro.', 'error');
        showModal('login');
        return; 
      }
      
      openCheckoutModal();
      await initPaymentBrick();
    }

    const btnClose = e.target.closest('#btn-close-checkout');
    if (btnClose) {
      closeCheckoutModal();
    }
  });

  document.addEventListener('chubut:retry-payment', async () => {
    await initPaymentBrick();
  });
}
