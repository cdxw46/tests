/**
 * PHANTOM CORP — Main JavaScript
 * Particles background + interactive effects
 */

// ─── Particles Background ───
(function initParticles() {
    const canvas = document.getElementById('particles');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let particles = [];
    const PARTICLE_COUNT = 60;
    const MAX_DIST = 120;

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    class Particle {
        constructor() {
            this.reset();
        }
        reset() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.vx = (Math.random() - 0.5) * 0.4;
            this.vy = (Math.random() - 0.5) * 0.4;
            this.radius = Math.random() * 1.5 + 0.5;
            this.alpha = Math.random() * 0.4 + 0.1;
        }
        update() {
            this.x += this.vx;
            this.y += this.vy;
            if (this.x < 0 || this.x > canvas.width) this.vx *= -1;
            if (this.y < 0 || this.y > canvas.height) this.vy *= -1;
        }
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(139, 92, 246, ${this.alpha})`;
            ctx.fill();
        }
    }

    for (let i = 0; i < PARTICLE_COUNT; i++) {
        particles.push(new Particle());
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Update & draw particles
        particles.forEach(p => {
            p.update();
            p.draw();
        });

        // Draw connections
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < MAX_DIST) {
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = `rgba(139, 92, 246, ${0.08 * (1 - dist / MAX_DIST)})`;
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                }
            }
        }

        requestAnimationFrame(animate);
    }
    animate();
})();

// ─── Console Easter Egg ───
console.log('%c' + [
    '╔══════════════════════════════════════════════════╗',
    '║          🔒 PHANTOM CORP SECURITY 🔒            ║',
    '║                                                  ║',
    '║  "The best defense is a good offense"            ║',
    '║                                                  ║',
    '║  Hint: Not everything that is encrypted          ║',
    '║        is also authenticated...                  ║',
    '║                                                  ║',
    '║  Auth: JWE (RSA-OAEP-256) + JWS (RS256)         ║',
    '║  JWKS: /.well-known/jwks.json                    ║',
    '║                                                  ║',
    '╚══════════════════════════════════════════════════╝',
].join('\n'), 'color: #8b5cf6; font-family: monospace; font-size: 11px;');

// ─── Terminal typing effect (login page) ───
(function initTerminal() {
    const terminal = document.getElementById('terminal-output');
    if (!terminal) return;

    const extraLines = [
        { text: '[*] Monitoring authentication attempts...', cls: 'term-cyan' },
        { text: '[+] TLS 1.3 handshake verified', cls: 'term-green' },
        { text: '[*] Token encryption: RSA-OAEP-256 + A256GCM', cls: 'term-cyan' },
        { text: '[*] Signature algorithm: RS256', cls: 'term-cyan' },
        { text: '[!] Remember: encryption ≠ authentication', cls: 'term-yellow' },
    ];

    let idx = 0;
    function addLine() {
        if (idx >= extraLines.length) return;
        const cursor = terminal.querySelector('.term-cursor');
        const p = document.createElement('p');
        const line = extraLines[idx];
        p.innerHTML = `<span class="${line.cls}">${line.text.substring(0, 3)}</span>${line.text.substring(3)}`;
        p.style.opacity = '0';
        terminal.insertBefore(p, cursor);
        requestAnimationFrame(() => { p.style.transition = 'opacity 0.3s'; p.style.opacity = '1'; });
        idx++;
        setTimeout(addLine, 2000 + Math.random() * 1500);
    }
    setTimeout(addLine, 3000);
})();
