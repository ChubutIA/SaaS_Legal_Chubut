import { state } from './state.js';
import { processPayment } from './api.js';
import { openCheckoutModal, closeCheckoutModal, showPaymentResult, showToast, showModal } from './ui.js';

// Tu clave pública de Mercado Pago
const MP_PUBLIC_KEY = 'APP_USR-58c1aa93-295b-4b5d-bb13-4de93f6b784e'; 
const PLAN_PRO_AMOUNT = 6500;

let brickController = null;

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
    container.innerHTML = '';
  }

  const mp = new MercadoPago(MP_PUBLIC_KEY, { locale: 'es-AR' });
  const bricksBuilder = mp.bricks();

  // Configuración ultra-simplificada a prueba de fallos
  const settings = {
    initialization: {
      amount: PLAN_PRO_AMOUNT,
      // Eliminamos la pre-carga del email por si eso estaba trabando el renderizado
    },
    customization: {
      visual: {
        style: {
          theme: 'dark',
          customVariables: {
            baseColor: '#c9a84c',
          }
        }
      }
      // Eliminamos las restricciones de "paymentMethods" para evitar conflictos
    },
    callbacks: {
      onReady: () => {
        console.log('Brick Renderizado exitosamente');
      },
      onSubmit: ({ selectedPaymentMethod, formData }) => {
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
