import { state } from './state.js';
import { processPayment } from './api.js';
import { openCheckoutModal, closeCheckoutModal, showPaymentResult, showToast, showModal } from './ui.js';

// Tu clave pública de Mercado Pago (¡Asegurate de usar la de PRUEBA que empieza con TEST-!)
const MP_PUBLIC_KEY = 'APP_USR-58c1aa93-295b-4b5d-bb13-4de93f6b784e'; 

let brickController = null;
let currentPlanType = 'mensual';

// Función para pedirle al backend el ID de preferencia y el monto
async function getPreferenceId(tipoPlan) {
  const res = await fetch('/api/payments/create-preference', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ tipo_plan: tipoPlan }),
    credentials: 'include' 
  });

  if (!res.ok) {
    throw new Error('No se pudo crear la preferencia de pago');
  }
  
  return await res.json();
}

export async function initPaymentBrick(tipoPlan = 'mensual') {
  currentPlanType = tipoPlan;
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

  let prefData;
  try {
    prefData = await getPreferenceId(tipoPlan);
  } catch (error) {
    console.error(error);
    if (container) container.innerHTML = 'Error al cargar el pago. Intentá de nuevo.';
    return;
  }

  const mp = new MercadoPago(MP_PUBLIC_KEY, { locale: 'es-AR' });
  const bricksBuilder = mp.bricks();

  const settings = {
    initialization: {
      amount: prefData.amount,
      preferenceId: prefData.preference_id,
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
        formData.tipo_plan = currentPlanType;
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
      
      const plan = btnOpen.dataset.plan || 'mensual';
      openCheckoutModal();
      await initPaymentBrick(plan);
    }

    const btnClose = e.target.closest('#btn-close-checkout');
    if (btnClose) {
      closeCheckoutModal();
    }
  });

  document.addEventListener('chubut:retry-payment', async () => {
    await initPaymentBrick(currentPlanType);
  });
}
