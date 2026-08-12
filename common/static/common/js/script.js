(function () {

    // Утилиты 
  
    function getCsrfToken() {
      return document.cookie.split(';')
        .map(c => c.trim())
        .find(c => c.startsWith('csrftoken='))
        ?.split('=')[1] ?? '';
    }
  
    function clearErrors(form) {
      form.querySelectorAll('[data-error-for]').forEach(el => el.textContent = '');
    }
  
    function showErrors(form, errors) {
      Object.entries(errors).forEach(([field, messages]) => {
        const el = form.querySelector(`[data-error-for="${field}"]`);
        if (el) el.textContent = (messages || []).join(' ');
      });
    }
  
    // Маска телефона: 8 XXX-XXX-XX-XX 
  
    const PHONE_TEMPLATE = [
      { type: 'digit' },
      { type: 'sep', ch: ' ' },
      { type: 'digit' }, { type: 'digit' }, { type: 'digit' },
      { type: 'sep', ch: '-' },
      { type: 'digit' }, { type: 'digit' }, { type: 'digit' },
      { type: 'sep', ch: '-' },
      { type: 'digit' }, { type: 'digit' },
      { type: 'sep', ch: '-' },
      { type: 'digit' }, { type: 'digit' },
    ];
    const PHONE_MAX_DIGITS = PHONE_TEMPLATE.filter(t => t.type === 'digit').length;
  
    function buildAndCaret(digits, targetDigitPos) {
      let di = 0, out = '', caretPos = -1;
      for (const slot of PHONE_TEMPLATE) {
        if (slot.type === 'digit') {
          if (di >= digits.length) break;
          out += digits[di];
          if (++di === targetDigitPos) caretPos = out.length;
        } else if (di > 0 && di < digits.length) {
          out += slot.ch;
        }
      }
      return { formatted: out, caretPos: caretPos === -1 ? out.length : caretPos };
    }
  
    function parseCaretInfo(val, s, end) {
      let digBefore = 0, digSel = 0;
      for (let i = 0; i < val.length; i++) {
        const c = val.charCodeAt(i);
        if (c < 48 || c > 57) continue;
        if (i < s)   digBefore++;
        if (i < end) digSel++;
      }
      return { digBefore, digInSel: digSel - digBefore };
    }
  
    function applyPhoneMask(input) {
      if (!input) return;
  
      function set(digits, caretDigitPos) {
        const { formatted, caretPos } = buildAndCaret(digits, caretDigitPos);
        input.value = formatted;
        input.setSelectionRange(caretPos, caretPos);
      }
  
      input.addEventListener('keydown', function (e) {
        if (e.ctrlKey || e.metaKey) return;
  
        const key = e.key;
        const nav = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Tab', 'Home', 'End'];
        if (nav.includes(key)) return;
  
        e.preventDefault();
  
        const val = input.value;
        const s   = input.selectionStart;
        const end = input.selectionEnd;
        const { digBefore, digInSel } = parseCaretInfo(val, s, end);
        const digits = val.replace(/\D/g, '');
  
        if (key === 'Backspace' || key === 'Delete') {
          if (digInSel > 0) {
            set(digits.slice(0, digBefore) + digits.slice(digBefore + digInSel), digBefore);
          } else if (key === 'Backspace') {
            if (digBefore <= 1) return;
            set(digits.slice(0, digBefore - 1) + digits.slice(digBefore), digBefore - 1);
          } else {
            if (digBefore >= digits.length) return;
            set(digits.slice(0, digBefore) + digits.slice(digBefore + 1), digBefore);
          }
          return;
        }
  
        if (key >= '0' && key <= '9') {
          if (digits.length - digInSel >= PHONE_MAX_DIGITS) return;
          const next = (digits.slice(0, digBefore) + key + digits.slice(digBefore + digInSel)).slice(0, PHONE_MAX_DIGITS);
          set(next, digBefore + 1);
        }
      });
  
      input.addEventListener('paste', function (e) {
        e.preventDefault();
        let d = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '');
        if (d.startsWith('7'))      d = '8' + d.slice(1);
        else if (!d.startsWith('8')) d = '8' + d;
        const { formatted } = buildAndCaret(d.slice(0, PHONE_MAX_DIGITS), Infinity);
        input.value = formatted;
        input.setSelectionRange(formatted.length, formatted.length);
      });
  
      input.addEventListener('focus', function () {
        if (!input.value) { input.value = '8'; input.setSelectionRange(1, 1); }
      });
  
      input.addEventListener('blur', function () {
        if (input.value === '8') input.value = '';
      });
  
      input.addEventListener('click', function () {
        if (input.selectionStart < 1) input.setSelectionRange(1, 1);
      });
    }
  
    // Тип заявки ───
  
    function setRequestType(type) {
      const input     = document.getElementById('purchase-request-type');
      const innBlock  = document.getElementById('inn-wrapper');
      const form      = document.getElementById('purchase-form');
      const submitBtn = form?.querySelector("button[type='submit']");
  
      if (!input) return;
      input.value = type;
  
      const isLeasing = type === 'leasing';
      if (innBlock)  innBlock.style.display  = isLeasing ? 'block' : 'none';
      if (submitBtn) submitBtn.textContent   = isLeasing
        ? 'Оставить заявку на лизинг'
        : 'Оставить заявку на покупку';
    }
  
    // Отправка ─────
  
    async function submitForm(form) {
      clearErrors(form);
  
      const submitBtn = form.querySelector("button[type='submit']");
      if (submitBtn) submitBtn.disabled = true;
  
      let resp, data;
  
      try {
        resp = await fetch(form.action, {
          method:  'POST',
          body:    new FormData(form),
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken':      getCsrfToken(),
          },
        });
  
        // Если сервер вернул не JSON — покажем понятную ошибку
        const contentType = resp.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
          console.error('Сервер вернул не JSON. Статус:', resp.status, await resp.text());
          showErrors(form, { __all__: ['Ошибка сервера. Попробуйте позже.'] });
          return;
        }
  
        data = await resp.json();
  
      } catch (err) {
        console.error('Ошибка сети:', err);
        showErrors(form, { __all__: ['Нет соединения. Попробуйте ещё раз.'] });
        return;
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
  
      if (!resp.ok || !data.ok) {
        showErrors(form, data.errors || { __all__: ['Произошла ошибка'] });
        return;
      }
  
      form.style.display = 'none';
      const success = document.getElementById('purchase-success');
      if (success) {
        success.textContent   = data.message || 'Спасибо, мы свяжемся с вами';
        success.style.display = 'block';
      }
    }
  
    // Инициализация 
  
    document.addEventListener('DOMContentLoaded', () => {
      const form = document.getElementById('purchase-form');
      if (!form) return;
  
      const titleInput = document.getElementById('purchase-vehicle-title');
      const titleView  = document.getElementById('purchase-vehicle-title-view');
  
      function syncVehicleTitle() {
        if (titleView) titleView.textContent = titleInput?.value.trim() || 'Не выбрано';
      }
      syncVehicleTitle();
  
      applyPhoneMask(document.getElementById('purchase-phone'));
  
      // Открытие формы через делегирование
      document.addEventListener('click', e => {
        const trigger = e.target.closest('[data-purchase-open]');
        if (!trigger) return;
        if (trigger.tagName === 'A') e.preventDefault();
  
        setRequestType(trigger.getAttribute('data-request-type') || 'purchase');
  
        const vehicleId    = document.getElementById('purchase-vehicle-id');
        const vehicleTitle = document.getElementById('purchase-vehicle-title');
  
        if (vehicleId)    vehicleId.value    = trigger.getAttribute('data-vehicle-id')    || '';
        if (vehicleTitle) vehicleTitle.value = trigger.getAttribute('data-vehicle-title') || '';
  
        form.style.display = '';
  
        const success = document.getElementById('purchase-success');
        if (success) { success.style.display = 'none'; success.textContent = ''; }
  
        clearErrors(form);
        syncVehicleTitle();
      });
  
      form.addEventListener('submit', e => {
        e.preventDefault();
        submitForm(form);
      });
    });
  
  })();