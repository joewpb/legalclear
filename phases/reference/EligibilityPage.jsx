import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Scale, CheckCircle2, XCircle, AlertCircle, ExternalLink, ArrowLeft } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

const US_STATES = [
  'Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut',
  'Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa',
  'Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan',
  'Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada',
  'New Hampshire','New Jersey','New Mexico','New York','North Carolina',
  'North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island',
  'South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont',
  'Virginia','Washington','West Virginia','Wisconsin','Wyoming',
  'Washington D.C.'
];

export default function EligibilityPage() {
  const [form, setForm] = useState({
    jurisdiction: 'Florida',
    offense_description: '',
    years_since_offense: '',
    lang: 'en'
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = e => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleCheck = async () => {
    if (!form.offense_description || !form.years_since_offense) {
      setError('Please fill in all fields.');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`${API_URL}/eligibility`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jurisdiction: form.jurisdiction,
          offense_description: form.offense_description,
          years_since_offense: parseInt(form.years_since_offense),
          lang: form.lang
        })
      });
      if (!res.ok) throw new Error('Could not check eligibility');
      setResult(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen pt-24 px-4 sm:px-6 flex flex-col items-center">
      <div className="max-w-2xl w-full animate-slide-up">

        <Link to="/" className="flex items-center gap-2 text-gray-400 hover:text-white text-sm mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to home
        </Link>

        <div className="text-center mb-10">
          <div className="w-16 h-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mx-auto mb-4">
            <Scale className="w-8 h-8 text-blue-400" />
          </div>
          <h1 className="text-4xl font-bold mb-3">Expungement Eligibility</h1>
          <p className="text-gray-400 leading-relaxed">
            Check whether a criminal record may qualify for expungement in your state.
            This is a free preliminary assessment — not legal advice.
          </p>
        </div>

        <div className="glass-card p-6 space-y-6">

          {/* Language toggle */}
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-sm">Language:</span>
            <button
              onClick={() => setForm(p => ({...p, lang: 'en'}))}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${form.lang === 'en' ? 'bg-blue-600 text-white' : 'bg-white/5 text-gray-400 hover:text-white'}`}
            >EN</button>
            <button
              onClick={() => setForm(p => ({...p, lang: 'es'}))}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${form.lang === 'es' ? 'bg-blue-600 text-white' : 'bg-white/5 text-gray-400 hover:text-white'}`}
            >ES</button>
          </div>

          {/* State selector */}
          <div>
            <label className="text-gray-400 text-xs uppercase tracking-wider mb-2 block">State</label>
            <select
              name="jurisdiction"
              value={form.jurisdiction}
              onChange={handleChange}
              className="w-full bg-zinc-900 border border-white/10 rounded-lg px-4 py-3 text-white text-sm outline-none focus:border-blue-500/50 transition-colors"
            >
              {US_STATES.map(state => (
                <option key={state} value={state}>{state}</option>
              ))}
            </select>
          </div>

          {/* Offense description */}
          <div>
            <label className="text-gray-400 text-xs uppercase tracking-wider mb-2 block">
              Describe the offense
            </label>
            <textarea
              name="offense_description"
              value={form.offense_description}
              onChange={handleChange}
              rows={3}
              placeholder="e.g. misdemeanor petit theft, first offense, no violence involved"
              className="w-full bg-zinc-900 border border-white/10 rounded-lg px-4 py-3 text-white text-sm outline-none focus:border-blue-500/50 transition-colors resize-none placeholder:text-gray-600"
            />
            <p className="text-gray-500 text-xs mt-1">
              Be as specific as possible. Include the charge name, degree, and any relevant details.
            </p>
          </div>

          {/* Years since offense */}
          <div>
            <label className="text-gray-400 text-xs uppercase tracking-wider mb-2 block">
              Years since the offense
            </label>
            <input
              type="number"
              name="years_since_offense"
              value={form.years_since_offense}
              onChange={handleChange}
              min="0"
              max="50"
              placeholder="e.g. 5"
              className="w-full bg-zinc-900 border border-white/10 rounded-lg px-4 py-3 text-white text-sm outline-none focus:border-blue-500/50 transition-colors placeholder:text-gray-600"
            />
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            onClick={handleCheck}
            disabled={loading}
            className="btn-primary w-full py-3 disabled:opacity-50"
          >
            {loading ? 'Checking eligibility...' : 'Check Eligibility'}
          </button>
        </div>

        {/* Result */}
        {result && (
          <div className="mt-8 space-y-6 animate-slide-up">

            {/* Eligible / Not eligible banner */}
            <div className={`p-6 rounded-2xl border flex items-start gap-4 ${
              result.likely_eligible
                ? 'bg-green-500/10 border-green-500/30'
                : 'bg-red-500/10 border-red-500/30'
            }`}>
              {result.likely_eligible
                ? <CheckCircle2 className="w-8 h-8 text-green-400 shrink-0 mt-0.5" />
                : <XCircle className="w-8 h-8 text-red-400 shrink-0 mt-0.5" />
              }
              <div>
                <h2 className={`text-xl font-bold mb-1 ${result.likely_eligible ? 'text-green-400' : 'text-red-400'}`}>
                  {result.likely_eligible ? 'Likely Eligible' : 'May Not Be Eligible'}
                  <span className="text-sm font-normal ml-2 opacity-70">
                    ({result.confidence} confidence)
                  </span>
                </h2>
                <p className="text-gray-300 text-sm leading-relaxed">{result.reasoning}</p>
              </div>
            </div>

            {/* Key factors */}
            {result.key_factors?.length > 0 && (
              <div className="glass-card p-6">
                <h3 className="text-lg font-bold text-white mb-4">Key factors considered</h3>
                <ul className="space-y-2 text-gray-300 text-sm">
                  {result.key_factors.map((factor, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-blue-400 mt-1">•</span>{factor}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Next steps */}
            {result.next_steps?.length > 0 && (
              <div className="glass-card p-6">
                <h3 className="text-lg font-bold text-white mb-4">Recommended next steps</h3>
                <ol className="space-y-2 text-gray-300 text-sm">
                  {result.next_steps.map((step, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-blue-500 font-bold mt-0.5">{i + 1}.</span>{step}
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {/* Disclaimer */}
            <div className="flex items-start gap-3 p-4 bg-yellow-500/10 rounded-xl border border-yellow-500/20 text-sm text-gray-300">
              <AlertCircle className="w-5 h-5 text-yellow-500 shrink-0 mt-0.5" />
              <p>
                {result.disclaimer ||
                  'This is a preliminary assessment only and is not legal advice. Eligibility varies by individual circumstances. Always verify with a licensed attorney or your local court.'}
              </p>
            </div>

            {/* Upload expungement petition CTA */}
            <div className="glass-card p-6 text-center">
              <p className="text-gray-400 mb-4 text-sm">
                Have an expungement petition to file? Upload it to get a complete step-by-step guide.
              </p>
              <Link to="/upload" className="btn-primary inline-flex items-center gap-2">
                <ExternalLink className="w-4 h-4" />
                Upload your petition
              </Link>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
