import { state } from './state.js';
import { processPayment } from './api.js';
import { openCheckoutModal, closeCheckoutModal, showPaymentResult, showToast, showModal } from './ui.js';

// Tu clave pública de Mercado Pago (¡Asegurate de usar la de PRUEBA que empieza con TEST-!)
const MP_PUBLIC_KEY = 'TEST-ACA_VA_MI_CLAVE_DE_PRUEBA'; 
const PLAN_PRO_AMOUNT = 6500;

let brickController = null;

// Función para pedirle al backend el ID de preferencia
async function getPreferenceId() {
  const token = localStorage.getItem('sb-tu_proyecto-auth-token'); 
  
  const res = await fetch('/api/payments/create-preference', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
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
    container.innerHTML = ''; // ACÁ BORRAMOS EL TEXTO DE "CARGANDO..."
  }

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
      preferenceId: preferenceId,
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
        // ACÁ LE DECIMOS QUE SOLO MUESTRE SALDO EN CUENTA Y OCULTE MERCADO CRÉDITO
        mercadoPago: ['wallet_purchase'] 
      }
    },
    callbacks: {
      onReady: () => {
        console.log('Brick Renderizado exitosamente');
      },
      onSubmit: ({ selectedPaymentMethod, formData }) => {
        if (selectedPaymentMethod === 'wallet_purchase') {
          return new Promise((resolve) => resolve());
        }

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
