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

  const settings = {
    initialization: {
      amount: PLAN_PRO_AMOUNT,
      payer: {
        // En este punto estamos 100% seguros de que el usuario existe
        email: state.user.email, 
      },
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
        ticket: 'none',
        atm: 'none'
      }
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

  brickController = await bricksBuilder.create('payment', 'payment-brick-container', settings);
}

export function setupCheckoutListeners() {
  // Escuchamos los clics a nivel global para que no se pierdan si la UI se actualiza
  document.body.addEventListener('click', async (e) => {
    
    // Si hicieron clic en el botón de Activar Plan Pro
    const btnOpen = e.target.closest('#btn-open-checkout');
    if (btnOpen) {
      // BARRERA DE SEGURIDAD: Verificar si inició sesión
      if (!state.user || !state.user.email) {
        showToast('Tenés que iniciar sesión o registrarte para suscribirte al Plan Pro.', 'error');
        showModal('login'); // Le abrimos el modal de login automáticamente
        return; // Frenamos la ejecución acá
      }
      
      // Si tiene sesión, abrimos el checkout normal
      openCheckoutModal();
      await initPaymentBrick();
    }

    // Si hicieron clic en cerrar la ventana de pago
    const btnClose = e.target.closest('#btn-close-checkout');
    if (btnClose) {
      closeCheckoutModal();
    }
  });

  // Escuchar si tocan el botón de "Intentar nuevamente" en caso de tarjeta rechazada
  document.addEventListener('chubut:retry-payment', async () => {
    await initPaymentBrick();
  });
}
