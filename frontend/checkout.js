import { state } from './state.js';
import { processPayment } from './api.js';
import { openCheckoutModal, closeCheckoutModal, showPaymentResult } from './ui.js';

const MP_PUBLIC_KEY = 'APP_USR-58c1aa93-295b-4b5d-bb13-4de93f6b784e'; 
const PLAN_PRO_AMOUNT = 3999;

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
        email: state.user?.email || '', 
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
        console.log('Brick Renderizado');
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
  // Asegurate de que tu botón para pagar en la web tenga el ID "btn-open-checkout"
  const btnOpen = document.getElementById('btn-open-checkout');
  if (btnOpen) {
    btnOpen.addEventListener('click', async () => {
      openCheckoutModal();
      await initPaymentBrick();
    });
  }

  const btnClose = document.getElementById('btn-close-checkout');
  if (btnClose) {
    btnClose.addEventListener('click', () => {
      closeCheckoutModal();
    });
  }

  document.addEventListener('chubut:retry-payment', async () => {
    await initPaymentBrick();
  });
}
