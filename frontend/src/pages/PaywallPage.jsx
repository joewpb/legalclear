import { useParams, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';
const API_KEY = import.meta.env.VITE_API_KEY || 'testkey123';

export default function PaywallPage() {
  const { documentId } = useParams();
  const { state } = useLocation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const price = state?.price || 10;
  const currency = state?.currency || "USD";
  const reason = state?.detail || "Unlock your full analysis";

  const handleCheckout = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/checkout/${documentId}`, {
        method: 'POST',
        headers: { 'X-API-Key': API_KEY, 'Content-Type': 'application/json' }
      });
      if (!res.ok) {
        alert("Checkout unavailable. Contact support.");
        setLoading(false);
        return;
      }
      const data = await res.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        alert("No checkout URL returned");
        setLoading(false);
      }
    } catch (e) {
      alert("Checkout error: " + e.message);
      setLoading(false);
    }
  };

  return (
    <div style={{
      maxWidth: 500, margin: '4rem auto', padding: '2rem',
      textAlign: 'center', fontFamily: 'Inter, sans-serif'
    }}>
      <h1>Unlock Your Analysis</h1>
      <p style={{ color: '#666', marginBottom: '2rem' }}>{reason}</p>
      <div style={{
        fontSize: '3rem', fontWeight: 700, marginBottom: '2rem'
      }}>
        ${price} <span style={{fontSize:'1rem',color:'#999'}}>{currency}</span>
      </div>
      <button
        onClick={handleCheckout}
        disabled={loading}
        style={{
          background: '#000', color: '#fff', padding: '1rem 2rem',
          fontSize: '1.1rem', border: 'none', borderRadius: '8px',
          cursor: loading ? 'wait' : 'pointer', width: '100%'
        }}
      >
        {loading ? 'Redirecting...' : 'Continue to Checkout →'}
      </button>
      <p style={{marginTop:'1.5rem',fontSize:'0.85rem',color:'#999'}}>
        Document ID: {documentId}
      </p>
    </div>
  );
}
