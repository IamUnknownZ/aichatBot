// Store only an anonymous bearer capability for this app, never API credentials.
function isCanonicalToken(token) {
    // For 32 bytes, the last base64url symbol has two unused low bits.
    return typeof token === 'string' && /^[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]$/.test(token);
}

export default function ({data, setStateValue}) {
    if (data?.identity?.token) return;
    if (typeof navigator !== 'undefined' && navigator.locks?.request) {
        navigator.locks.request('ai-learning-studio-owner-initialization', () => {
            initialize(setStateValue);
        }).catch(() => initialize(setStateValue));
        return;
    }
    initialize(setStateValue);
}

function initialize(setStateValue) {
    const key = 'ai-learning-studio.browser-owner.v1';
    let token;
    let persisted = false;
    try {
        token = localStorage.getItem(key);
        if (!isCanonicalToken(token)) {
            const raw = crypto.getRandomValues(new Uint8Array(32));
            token = btoa(String.fromCharCode(...raw)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
            try {
                localStorage.setItem(key, token);
            } catch (_) {}
            try {
                const stored = localStorage.getItem(key);
                if (isCanonicalToken(stored)) {
                    token = stored;
                    persisted = true;
                }
            } catch (_) {}
        } else {
            persisted = true;
        }
    } catch (_) {
        const raw = crypto.getRandomValues(new Uint8Array(32));
        token = btoa(String.fromCharCode(...raw)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    }
    setStateValue('identity', {token, persisted});
}
