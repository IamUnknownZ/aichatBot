// Store only an anonymous bearer capability for this app, never API credentials.
export default function ({data, setStateValue}) {
    if (data?.identity?.token) return;
    const key = 'ai-learning-studio.browser-owner.v1';
    let token;
    let persisted = false;
    try {
        token = localStorage.getItem(key);
        if (!token || !/^[A-Za-z0-9_-]{43}$/.test(token)) {
            const raw = crypto.getRandomValues(new Uint8Array(32));
            token = btoa(String.fromCharCode(...raw)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
            localStorage.setItem(key, token);
        }
        persisted = true;
    } catch (_) {
        const raw = crypto.getRandomValues(new Uint8Array(32));
        token = btoa(String.fromCharCode(...raw)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    }
    setStateValue('identity', {token, persisted});
}
