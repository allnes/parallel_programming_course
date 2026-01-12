(() => {
  function norm(s) {
    if (!s) return '';
    s = s.normalize('NFKC').trim().toLowerCase();
    s = s.replaceAll('ё', 'е');
    s = s.replace(/\s+/g, ' ');
    return s;
  }

  async function sha256Bytes(str) {
    if (window.crypto && window.crypto.subtle) {
      const enc = new TextEncoder();
      const buf = enc.encode(str);
      const hash = await crypto.subtle.digest('SHA-256', buf);
      return new Uint8Array(hash);
    }
    // Fallback SHA-256 (small JS implementation)
    return new Uint8Array(hexToBytes(sha256Fallback(str)));
  }

  function hexToBytes(hex) {
    const out = [];
    for (let i = 0; i < hex.length; i += 2) out.push(parseInt(hex.substr(i, 2), 16));
    return out;
  }

  // Minimal SHA-256 fallback (public domain)
  function sha256Fallback(ascii) {
    function rightRotate(value, amount) { return (value>>>amount) | (value<<(32 - amount)); }
    var mathPow = Math.pow, maxWord = mathPow(2, 32);
    var words = [], asciiBitLength = ascii.length*8;
    var hash = sha256Fallback.h = sha256Fallback.h || [];
    var k = sha256Fallback.k = sha256Fallback.k || [];
    var primeCounter = k.length;
    var isComposite = {};
    for (var candidate = 2; primeCounter < 64; candidate++) {
      if (!isComposite[candidate]) {
        for (var i = 0; i < 313; i += candidate) isComposite[i] = candidate;
        hash[primeCounter] = (mathPow(candidate, .5)*maxWord)|0;
        k[primeCounter++] = (mathPow(candidate, 1/3)*maxWord)|0;
      }
    }
    ascii += '\x80';
    while (ascii.length%64 - 56) ascii += '\x00';
    for (i = 0; i < ascii.length; i++) {
      words[i>>2] |= ascii.charCodeAt(i) << ((3 - i)%4)*8;
    }
    words[words.length] = (asciiBitLength/maxWord)|0;
    words[words.length] = asciiBitLength;
    for (var j = 0; j < words.length;) {
      var w = words.slice(j, j += 16);
      var oldHash = hash.slice(0);
      hash = hash.slice(0, 8);
      for (i = 0; i < 64; i++) {
        var w15 = w[i - 15], w2 = w[i - 2];
        var a = hash[0], e = hash[4];
        var temp1 = hash[7]
          + (rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25))
          + ((e&hash[5])^((~e)&hash[6]))
          + k[i]
          + (w[i] = (i < 16) ? w[i] : (w[i - 16] + (rightRotate(w15, 7) ^ rightRotate(w15, 18) ^ (w15>>>3)) + w[i - 7] + (rightRotate(w2, 17) ^ rightRotate(w2, 19) ^ (w2>>>10)))|0);
        var temp2 = (rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22)) + ((a&hash[1])^(a&hash[2])^(hash[1]&hash[2]));
        hash = [(temp1 + temp2)|0].concat(hash);
        hash[4] = (hash[4] + temp1)|0;
      }
      for (i = 0; i < 8; i++) hash[i] = (hash[i] + oldHash[i])|0;
    }
    var result = '';
    for (i = 0; i < 8; i++) {
      for (j = 3; j + 1; j--) {
        var b = (hash[i] >> (j*8)) & 255;
        result += ((b < 16) ? 0 : '') + b.toString(16);
      }
    }
    return result;
  }

  async function computeThreadsVariant(student, repoSalt, vmax) {
    if (!vmax || vmax < 1) return null;
    const base = [
      norm(student.last_name),
      norm(student.first_name),
      norm(student.middle_name),
      norm(student.group_number),
      norm(repoSalt),
    ];
    if (!base[0] || !base[1] || !base[3]) return null;
    const bytes = await sha256Bytes(base.join('|'));
    let r = 0;
    for (const b of bytes) r = (r * 256 + b) % vmax;
    return r + 1;
  }

  async function computeProcessesVariants(student, repoSalt, vmaxes) {
    if (!Array.isArray(vmaxes) || vmaxes.length !== 3) return null;
    const base = [
      norm(student.last_name),
      norm(student.first_name),
      norm(student.middle_name),
      norm(student.group_number),
    ];
    if (!base[0] || !base[1] || !base[3]) return null;
    const res = [];
    for (let n = 1; n <= 3; n++) {
      const m = vmaxes[n - 1] || 1;
      const key = [...base, norm(`${repoSalt}/processes/task-${n}`)].join('|');
      const bytes = await sha256Bytes(key);
      let r = 0;
      for (const b of bytes) r = (r * 256 + b) % m;
      res.push(r + 1);
    }
    return res;
  }

  function studentFromDataset(el) {
    return {
      last_name: el.dataset.last || '',
      first_name: el.dataset.first || '',
      middle_name: el.dataset.middle || '',
      group_number: el.dataset.group || '',
    };
  }

  async function fillThreadsTable(repoSalt, vmax) {
    const rows = document.querySelectorAll('tr[data-last]');
    for (const tr of rows) {
      const v = await computeThreadsVariant(studentFromDataset(tr), repoSalt, vmax);
      if (v && tr.querySelector('.variant-cell')) tr.querySelector('.variant-cell').textContent = v;
    }
  }

  async function fillProcessesTable(repoSalt, vmaxes) {
    const rows = document.querySelectorAll('tr[data-last]');
    for (const tr of rows) {
      const vs = await computeProcessesVariants(studentFromDataset(tr), repoSalt, vmaxes);
      if (vs && tr.querySelector('.variant-cell')) tr.querySelector('.variant-cell').innerHTML = vs.join('<br/>');
    }
  }

  function attachForm(repoSalt, threadsVmax, procVmaxes) {
    const radios = document.querySelectorAll('input[name=sem]');
    const btn = document.getElementById('v_calc');
    if (!btn) return;
    btn.addEventListener('click', async () => {
      const sem = Array.from(radios || []).find((r) => r.checked)?.value || 'threads';
      const student = {
        last_name: document.getElementById('v_last').value,
        first_name: document.getElementById('v_first').value,
        middle_name: document.getElementById('v_middle').value,
        group_number: document.getElementById('v_group').value,
      };
      const res = document.getElementById('v_result');
      try {
        if (sem === 'threads') {
          const tv = await computeThreadsVariant(student, repoSalt, threadsVmax);
          if (!tv) throw new Error('Fill Last, First, Group');
          res.style.color = '#2563eb';
          res.innerHTML = `Threads: <b>${tv} of ${threadsVmax}</b>`;
        } else {
          const pv = await computeProcessesVariants(student, repoSalt, procVmaxes);
          if (!pv) throw new Error('Fill Last, First, Group');
          res.style.color = '#2563eb';
          res.innerHTML = `Processes: <b>${pv[0]} / ${pv[1]} / ${pv[2]}</b>`;
        }
      } catch (e) {
        res.textContent = 'Fill Last, First, Group';
        res.style.color = '#dc2626';
      }
    });
  }

  window.variantCalc = {
    fillThreadsTable,
    fillProcessesTable,
    attachForm,
  };
})();
