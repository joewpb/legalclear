import { useState, useEffect } from 'react';
import { useLocation, Link } from 'react-router-dom';
import {
  AlertOctagon, CheckCircle2, AlertTriangle, FileText,
  Settings, ShieldAlert, FileCheck, MessageSquare,
  Home, Upload, BarChart2, Bell, Loader2, Scale,
  BookOpen, MapPin, ExternalLink
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';
const API_KEY = import.meta.env.VITE_API_KEY || 'testkey123';

export default function AnalysisDashboard() {
  const location = useLocation();
  const [activeTab, setActiveTab] = useState('summary');
  const document_id =
    location.state?.document_id ||
    sessionStorage.getItem('lc_document_id');

  const [docData, setDocData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!document_id) {
      setError('No document found. Please upload a document first.');
      setLoading(false);
      return;
    }
    fetch(`${API_URL}/document/${document_id}`, {
      headers: { 'x-api-key': API_KEY }
    })
      .then(r => { if (!r.ok) throw new Error(`Failed to load: ${r.status}`); return r.json(); })
      .then(data => setDocData(data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [document_id]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex flex-col items-center gap-4 text-gray-400">
        <Loader2 className="w-10 h-10 animate-spin text-primary" />
        <p>Loading analysis...</p>
      </div>
    </div>
  );

  if (error) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-4">
        <p className="text-red-400 text-lg">{error}</p>
        <Link to="/upload" className="btn-primary">Upload a document</Link>
      </div>
    </div>
  );

  const explanation = docData?.explanation || {};
  const classification = docData?.classification || {};
  const riskScan = docData?.risk_scan || {};
  const formGuide = docData?.form_guide || {};
  const expungement = docData?.expungement_guide || {};
  const escalation = docData?.escalation || {};
  const category = classification?.document_category || '';

  const showFormGuide = formGuide && Object.keys(formGuide).length > 0;
  const showExpungement = expungement && Object.keys(expungement).length > 0;
  const showFlorida = classification?.jurisdiction_name === 'Florida' &&
    category.includes('small_claims');

  return (
    <div className="min-h-screen bg-background flex flex-col md:flex-row">
      <div className="w-full md:w-20 lg:w-64 bg-zinc-900 border-r border-white/5 flex flex-col">
        <div className="h-16 flex items-center justify-center lg:justify-start lg:px-6 border-b border-white/5">
          <span className="font-display font-bold text-xl text-white hidden lg:block">LegalClear</span>
        </div>
        <div className="flex-1 py-6 flex flex-col gap-2 px-3">
          <SidebarLink icon={<Home />} label="Home" to="/" />
          <SidebarLink icon={<Upload />} label="Upload" to="/upload" />
          <SidebarLink icon={<BarChart2 />} label="Dashboard" active to="/dashboard" />
          <SidebarLink icon={<Scale />} label="Eligibility" to="/eligibility" />
          <SidebarLink icon={<Settings />} label="Settings" to="#" />
        </div>
      </div>

      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        <header className="h-16 flex items-center justify-between px-6 bg-background/50 backdrop-blur-md border-b border-white/10 shrink-0 z-10">
          <div className="px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 text-xs font-semibold tracking-wider border border-blue-500/20 uppercase hidden sm:block">
            {classification.document_type || 'Legal Document'}
          </div>
          {escalation?.pre_analysis_warning && (
            <div className="flex-1 mx-4 px-3 py-1 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs hidden md:block truncate">
              ⚠ {escalation.pre_analysis_warning.slice(0, 80)}...
            </div>
          )}
          <div className="flex items-center gap-4">
            <Bell className="w-5 h-5 text-gray-400" />
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-medium text-sm">JD</div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="mb-8">
            <h1 className="text-3xl md:text-4xl font-display font-bold mb-3 tracking-tight">
              {classification.document_type || 'Document Analysis'}
            </h1>
            <p className="text-gray-400 flex items-center gap-2 text-sm">
              {classification.jurisdiction_name || 'Unknown jurisdiction'}
              <span className="w-1 h-1 rounded-full bg-gray-600" />
              {classification.estimated_complexity || 'Unknown'} complexity
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            <div className="lg:col-span-1 space-y-2">
              <TabButton active={activeTab === 'summary'} onClick={() => setActiveTab('summary')} icon={<FileText />} label="Summary & Rights" />
              <TabButton active={activeTab === 'risk'} onClick={() => setActiveTab('risk')} icon={<ShieldAlert />} label="Risk Scanner" alertCount={riskScan.red_count || 0} />
              {showFormGuide && <TabButton active={activeTab === 'form'} onClick={() => setActiveTab('form')} icon={<FileCheck />} label="Form Guide" />}
              {showExpungement && <TabButton active={activeTab === 'expungement'} onClick={() => setActiveTab('expungement')} icon={<BookOpen />} label="Expungement" />}
              {showFlorida && <TabButton active={activeTab === 'florida'} onClick={() => setActiveTab('florida')} icon={<MapPin />} label="File in Florida" />}
              <TabButton active={activeTab === 'chat'} onClick={() => setActiveTab('chat')} icon={<MessageSquare />} label="Ask AI" />
            </div>

            <div className="lg:col-span-3">
              <div className="bg-zinc-900/50 backdrop-blur-sm border border-white/5 hover:border-blue-500/50 transition-colors duration-500 min-h-[500px] rounded-2xl p-6 md:p-8 shadow-2xl">
                {activeTab === 'summary' && <SummaryView explanation={explanation} escalation={escalation} />}
                {activeTab === 'risk' && <RiskView riskScan={riskScan} />}
                {activeTab === 'form' && <FormGuideView formGuide={formGuide} />}
                {activeTab === 'expungement' && <ExpungementView expungement={expungement} />}
                {activeTab === 'florida' && <FloridaFilingView classification={classification} />}
                {activeTab === 'chat' && <ChatView documentId={document_id} />}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SidebarLink({ icon, label, active, to }) {
  return (
    <Link to={to} className={`flex items-center gap-3 w-full p-3 rounded-xl transition-all ${active ? 'bg-blue-600/10 text-blue-500' : 'text-gray-500 hover:bg-white/5 hover:text-gray-300'}`}>
      <div className={`w-6 h-6 flex justify-center items-center ${active ? 'opacity-100' : 'opacity-60'}`}>{icon}</div>
      <span className="font-medium hidden lg:block">{label}</span>
    </Link>
  );
}

function TabButton({ active, onClick, icon, label, alertCount }) {
  return (
    <button onClick={onClick} className={`w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all font-medium text-left ${active ? 'bg-gradient-to-tr from-blue-600 to-indigo-500 text-white shadow-lg shadow-blue-500/25' : 'bg-zinc-900/30 text-gray-400 hover:bg-zinc-800 hover:text-white border border-transparent'}`}>
      <div className="flex items-center gap-3">
        <div className={`w-5 h-5 ${active ? 'opacity-100' : 'opacity-60'}`}>{icon}</div>
        {label}
      </div>
      {alertCount > 0 && <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${active ? 'bg-white text-blue-600' : 'bg-red-500/20 text-red-500'}`}>{alertCount}</span>}
    </button>
  );
}

function SummaryView({ explanation, escalation }) {
  if (!explanation?.summary) return <div className="text-gray-400 text-center py-12">No summary available.</div>;
  return (
    <div className="space-y-8 animate-slide-up">
      {escalation?.pre_analysis_warning && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
          <strong className="text-red-400">Important: </strong>{escalation.pre_analysis_warning}
        </div>
      )}
      <div>
        <h2 className="text-2xl font-bold mb-4 font-display">Plain Language Summary</h2>
        <p className="text-gray-300 text-lg leading-relaxed">{explanation.summary}</p>
      </div>
      {explanation.what_this_means_for_you && (
        <div className="bg-zinc-800/30 border border-blue-500/20 rounded-xl p-6">
          <h3 className="text-lg font-bold text-blue-400 mb-3">What this means for you</h3>
          <p className="text-gray-300 leading-relaxed">{explanation.what_this_means_for_you}</p>
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {explanation.your_rights?.length > 0 && (
          <div className="bg-zinc-800/30 border border-green-500/20 rounded-xl p-6">
            <h3 className="text-lg font-bold text-green-400 flex items-center gap-2 mb-4"><CheckCircle2 className="w-5 h-5" /> Your Rights</h3>
            <ul className="space-y-3 text-gray-300">{explanation.your_rights.map((r, i) => <li key={i} className="flex items-start gap-2"><span className="text-green-500 mt-1">•</span>{r}</li>)}</ul>
          </div>
        )}
        {explanation.your_obligations?.length > 0 && (
          <div className="bg-zinc-800/30 border border-blue-500/20 rounded-xl p-6">
            <h3 className="text-lg font-bold text-blue-400 flex items-center gap-2 mb-4"><FileCheck className="w-5 h-5" /> Your Obligations</h3>
            <ul className="space-y-3 text-gray-300">{explanation.your_obligations.map((o, i) => <li key={i} className="flex items-start gap-2"><span className="text-blue-500 mt-1">•</span>{o}</li>)}</ul>
          </div>
        )}
      </div>
      {explanation.important_numbers?.length > 0 && (
        <div className="bg-zinc-800/30 border border-purple-500/20 rounded-xl p-6">
          <h3 className="text-lg font-bold text-purple-400 mb-4">Key Numbers & Dates</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {explanation.important_numbers.map((n, i) => (
              <div key={i} className="bg-black/20 rounded-lg p-3">
                <div className="text-white font-bold">{n.value}</div>
                <div className="text-gray-400 text-sm">{n.label}</div>
                {n.context && <div className="text-gray-500 text-xs mt-1">{n.context}</div>}
              </div>
            ))}
          </div>
        </div>
      )}
      {explanation.questions_to_ask?.length > 0 && (
        <div className="bg-zinc-800/30 border border-yellow-500/20 rounded-xl p-6">
          <h3 className="text-lg font-bold text-yellow-400 mb-4">Questions to ask before signing</h3>
          <ol className="space-y-2 text-gray-300">{explanation.questions_to_ask.map((q, i) => <li key={i} className="flex items-start gap-2"><span className="text-yellow-500 font-bold mt-0.5">{i+1}.</span>{q}</li>)}</ol>
        </div>
      )}
      {escalation?.resource_links?.length > 0 && (
        <div className="bg-zinc-800/30 border border-white/10 rounded-xl p-6">
          <h3 className="text-lg font-bold text-gray-300 mb-4">Legal Resources</h3>
          <div className="space-y-2">{escalation.resource_links.map((link, i) => (
            <a key={i} href={link.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-blue-400 hover:text-blue-300 text-sm">
              <ExternalLink className="w-4 h-4 shrink-0" />{link.label}
            </a>
          ))}</div>
        </div>
      )}
    </div>
  );
}

function RiskView({ riskScan }) {
  if (!riskScan?.overall_risk_level) return <div className="text-gray-400 text-center py-12">No risk scan available.</div>;
  const levelColor = {HIGH:'text-red-400 border-red-500/30 bg-red-500/5',MEDIUM:'text-yellow-400 border-yellow-500/30 bg-yellow-500/5',LOW:'text-green-400 border-green-500/30 bg-green-500/5'}[riskScan.overall_risk_level]||'text-gray-400 border-white/10';
  return (
    <div className="space-y-6 animate-slide-up">
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 mb-6">
        <div><h2 className="text-3xl font-display font-bold mb-2">Risk Scanner</h2><p className="text-gray-400">{riskScan.risk_summary}</p></div>
        <div className={`px-4 py-2 rounded-xl border font-bold text-lg whitespace-nowrap ${levelColor}`}>{riskScan.overall_risk_level} RISK</div>
      </div>
      {riskScan.top_concerns?.length > 0 && (
        <div className="bg-zinc-800/30 border border-white/5 rounded-xl p-4 mb-2">
          <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">Top concerns</h3>
          <ol className="space-y-2">{riskScan.top_concerns.map((c,i)=><li key={i} className="text-gray-300 flex items-start gap-2 text-sm"><span className="text-red-400 font-bold mt-0.5">{i+1}.</span>{c}</li>)}</ol>
        </div>
      )}
      <div className="space-y-4">{(riskScan.clauses||[]).map((clause,i)=><RiskItem key={i} clause={clause}/>)}</div>
      {riskScan.missing_protections?.length > 0 && (
        <div className="bg-zinc-800/30 border border-orange-500/20 rounded-xl p-6 mt-4">
          <h3 className="text-lg font-bold text-orange-400 mb-4">Missing Protections</h3>
          <div className="space-y-4">{riskScan.missing_protections.map((p,i)=>(
            <div key={i} className="border-l-2 border-orange-500/50 pl-4">
              <div className="font-bold text-white">{p.protection_name}</div>
              <div className="text-gray-400 text-sm mt-1">{p.why_important}</div>
              <div className="text-orange-400 text-sm mt-1">Ask for: {p.what_to_ask_for}</div>
            </div>
          ))}</div>
        </div>
      )}
      {riskScan.negotiation_tips?.length > 0 && (
        <div className="bg-zinc-800/30 border border-teal-500/20 rounded-xl p-6">
          <h3 className="text-lg font-bold text-teal-400 mb-4">Negotiation Tips</h3>
          <ul className="space-y-2 text-gray-300">{riskScan.negotiation_tips.map((tip,i)=><li key={i} className="flex items-start gap-2"><span className="text-teal-400 mt-1">•</span>{tip}</li>)}</ul>
        </div>
      )}
    </div>
  );
}

function RiskItem({ clause }) {
  const isRed=clause.risk_level==='RED', isYellow=clause.risk_level==='YELLOW';
  const colorClass=isRed?'text-red-400':isYellow?'text-yellow-400':'text-green-400';
  const borderClass=isRed?'border-red-500/30':isYellow?'border-yellow-500/30':'border-green-500/30';
  const bgClass=isRed?'bg-red-500/5':isYellow?'bg-yellow-500/5':'bg-green-500/5';
  const barClass=isRed?'bg-red-500':isYellow?'bg-yellow-500':'bg-green-500';
  const Icon=isRed?AlertOctagon:AlertTriangle;
  return (
    <div className={`p-6 rounded-xl border ${borderClass} ${bgClass} relative overflow-hidden transition-all hover:bg-zinc-800/50`}>
      <div className={`absolute top-0 left-0 w-1 h-full ${barClass}`}/>
      <div className="flex items-start gap-4">
        <Icon className={`w-6 h-6 mt-1 flex-shrink-0 ${colorClass}`}/>
        <div className="flex-1">
          <h3 className={`text-lg font-bold mb-2 ${colorClass}`}>{clause.clause_title}</h3>
          {clause.quote&&<p className="text-sm font-mono bg-black/40 text-gray-300 p-3 rounded border border-white/5 mb-4 border-l-4 border-l-zinc-600">"{clause.quote}"</p>}
          <p className="text-gray-300 mb-3"><strong className="text-white">Why it matters:</strong> {clause.why_it_matters}</p>
          <p className="text-gray-300"><strong className="text-white">What to do:</strong> {clause.what_to_do}</p>
        </div>
      </div>
    </div>
  );
}

function FormGuideView({ formGuide }) {
  if (!formGuide?.form_overview) return <div className="text-gray-400 text-center py-12">No form guide available.</div>;
  return (
    <div className="space-y-8 animate-slide-up">
      <div><h2 className="text-2xl font-bold mb-4 font-display">Form Completion Guide</h2><p className="text-gray-300 leading-relaxed">{formGuide.form_overview}</p></div>
      {formGuide.deadline_warning&&<div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-sm"><strong className="text-red-400">⏰ Deadline: </strong>{formGuide.deadline_warning}</div>}
      {formGuide.before_you_start?.length>0&&(
        <div className="bg-zinc-800/30 border border-yellow-500/20 rounded-xl p-6">
          <h3 className="text-lg font-bold text-yellow-400 mb-4">Before you start — gather these</h3>
          <ul className="space-y-2 text-gray-300">{formGuide.before_you_start.map((item,i)=><li key={i} className="flex items-start gap-2"><span className="text-yellow-400 mt-1">□</span>{item}</li>)}</ul>
        </div>
      )}
      {formGuide.sections?.map((section,i)=>(
        <div key={i} className="bg-zinc-800/30 border border-white/5 rounded-xl p-6">
          <h3 className="text-lg font-bold text-white mb-2">{section.section_name}</h3>
          <p className="text-gray-400 text-sm mb-4">{section.description}</p>
          <div className="space-y-4">{section.fields?.map((field,j)=>(
            <div key={j} className="border-l-2 border-blue-500/30 pl-4">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-bold text-white">{field.plain_label}</span>
                {field.required&&<span className="text-xs text-red-400 font-bold">REQUIRED</span>}
                {field.field_number&&<span className="text-xs text-gray-500">Field {field.field_number}</span>}
              </div>
              <p className="text-gray-300 text-sm">{field.instructions}</p>
              {field.example&&<p className="text-blue-400 text-sm mt-1">Example: {field.example}</p>}
              {field.common_mistakes&&<p className="text-red-400 text-xs mt-1">⚠ Common mistake: {field.common_mistakes}</p>}
            </div>
          ))}</div>
        </div>
      ))}
      {formGuide.where_to_file&&(
        <div className="bg-zinc-800/30 border border-green-500/20 rounded-xl p-6">
          <h3 className="text-lg font-bold text-green-400 mb-4">Where to file</h3>
          <div className="space-y-2 text-gray-300 text-sm">
            {formGuide.where_to_file.fee&&<p><strong className="text-white">Filing fee:</strong> {formGuide.where_to_file.fee}</p>}
            {formGuide.where_to_file.online_url&&<a href={formGuide.where_to_file.online_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-blue-400 hover:text-blue-300"><ExternalLink className="w-4 h-4"/>File online</a>}
          </div>
        </div>
      )}
      {formGuide.small_claims_hearing_tips?.length>0&&(
        <div className="bg-zinc-800/30 border border-teal-500/20 rounded-xl p-6">
          <h3 className="text-lg font-bold text-teal-400 mb-4">Hearing Tips</h3>
          <ul className="space-y-2 text-gray-300">{formGuide.small_claims_hearing_tips.map((tip,i)=><li key={i} className="flex items-start gap-2"><span className="text-teal-400 mt-1">•</span>{tip}</li>)}</ul>
        </div>
      )}
    </div>
  );
}

function ExpungementView({ expungement }) {
  if (!expungement?.what_is_expungement) return <div className="text-gray-400 text-center py-12">No expungement guide available.</div>;
  return (
    <div className="space-y-8 animate-slide-up">
      <div><h2 className="text-2xl font-bold mb-4 font-display">Expungement Guide</h2><p className="text-gray-300 leading-relaxed">{expungement.what_is_expungement}</p></div>
      {expungement.eligibility_overview&&<div className="bg-zinc-800/30 border border-blue-500/20 rounded-xl p-6"><h3 className="text-lg font-bold text-blue-400 mb-3">Eligibility Overview</h3><p className="text-gray-300 text-sm leading-relaxed">{expungement.eligibility_overview}</p></div>}
      {expungement.before_you_start?.length>0&&(
        <div className="bg-zinc-800/30 border border-yellow-500/20 rounded-xl p-6">
          <h3 className="text-lg font-bold text-yellow-400 mb-4">Documents to gather</h3>
          <ul className="space-y-2 text-gray-300">{expungement.before_you_start.map((item,i)=><li key={i} className="flex items-start gap-2"><span className="text-yellow-400 mt-1">□</span>{item}</li>)}</ul>
        </div>
      )}
      {expungement.steps?.length>0&&(
        <div className="space-y-4">
          <h3 className="text-xl font-bold text-white">Step-by-step process</h3>
          {expungement.steps.map((step,i)=>(
            <div key={i} className="bg-zinc-800/30 border border-white/5 rounded-xl p-6 relative pl-10">
              <div className="absolute left-3 top-6 w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold">{step.step_number||i+1}</div>
              <h4 className="font-bold text-white mb-2">{step.title}</h4>
              <p className="text-gray-300 text-sm mb-2">{step.instructions}</p>
              {step.tips&&<p className="text-blue-400 text-xs">💡 {step.tips}</p>}
              <div className="flex gap-4 mt-2">
                {step.estimated_time&&<span className="text-gray-500 text-xs">⏱ {step.estimated_time}</span>}
                {step.cost&&<span className="text-gray-500 text-xs">💰 {step.cost}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {expungement.what_changes_after?.length>0&&(
          <div className="bg-zinc-800/30 border border-green-500/20 rounded-xl p-6">
            <h3 className="text-lg font-bold text-green-400 mb-4">What changes after</h3>
            <ul className="space-y-2 text-gray-300 text-sm">{expungement.what_changes_after.map((item,i)=><li key={i} className="flex items-start gap-2"><span className="text-green-400 mt-0.5">✓</span>{item}</li>)}</ul>
          </div>
        )}
        {expungement.what_does_not_change?.length>0&&(
          <div className="bg-zinc-800/30 border border-orange-500/20 rounded-xl p-6">
            <h3 className="text-lg font-bold text-orange-400 mb-4">Important limitations</h3>
            <ul className="space-y-2 text-gray-300 text-sm">{expungement.what_does_not_change.map((item,i)=><li key={i} className="flex items-start gap-2"><span className="text-orange-400 mt-0.5">✗</span>{item}</li>)}</ul>
          </div>
        )}
      </div>
      {expungement.free_resources?.length>0&&(
        <div className="bg-zinc-800/30 border border-white/10 rounded-xl p-6">
          <h3 className="text-lg font-bold text-gray-300 mb-4">Free Resources</h3>
          <div className="space-y-3">{expungement.free_resources.map((r,i)=>(
            <div key={i}>
              <a href={r.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-blue-400 hover:text-blue-300 font-medium"><ExternalLink className="w-4 h-4 shrink-0"/>{r.label}</a>
              {r.description&&<p className="text-gray-500 text-xs mt-1 ml-6">{r.description}</p>}
            </div>
          ))}</div>
        </div>
      )}
    </div>
  );
}

function FloridaFilingView({ classification }) {
  const [loading, setLoading] = useState(false);
  const [packet, setPacket] = useState(null);
  const [error, setError] = useState(null);
  const [caseData, setCaseData] = useState({
    plaintiff_name:'', plaintiff_address:'', plaintiff_city_state_zip:'',
    plaintiff_phone:'', defendant_name:'', defendant_address:'',
    defendant_city_state_zip:'', amount_claimed:'', claim_reason:'',
    incident_date:'', county:'',
  });

  const handleChange = e => setCaseData(prev => ({...prev, [e.target.name]: e.target.value}));

  const handlePrepare = async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API_URL}/florida-filing/prepare`, {
        method:'POST', headers:{'x-api-key':API_KEY,'Content-Type':'application/json'},
        body: JSON.stringify(caseData)
      });
      if (!res.ok) throw new Error('Failed to prepare filing packet');
      setPacket(await res.json());
    } catch(err) { setError(err.message); }
    finally { setLoading(false); }
  };

  const fields = [
    {name:'plaintiff_name',label:'Your full legal name'},
    {name:'plaintiff_address',label:'Your street address'},
    {name:'plaintiff_city_state_zip',label:'Your city, state, zip'},
    {name:'plaintiff_phone',label:'Your phone number'},
    {name:'defendant_name',label:'Defendant name or business'},
    {name:'defendant_address',label:'Defendant street address'},
    {name:'defendant_city_state_zip',label:'Defendant city, state, zip'},
    {name:'amount_claimed',label:'Amount claimed ($)'},
    {name:'incident_date',label:'Date of incident (YYYY-MM-DD)'},
    {name:'county',label:'Florida county'},
  ];

  return (
    <div className="space-y-8 animate-slide-up">
      <div>
        <h2 className="text-2xl font-bold mb-2 font-display">File in Florida Court</h2>
        <p className="text-gray-400 text-sm">Generate your small claims filing packet and submit via MyFLCourtAccess.</p>
      </div>
      {!packet ? (
        <div className="space-y-4">
          <h3 className="text-lg font-bold text-white">Your case information</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {fields.map(field=>(
              <div key={field.name}>
                <label className="text-gray-400 text-xs uppercase tracking-wider mb-1 block">{field.label}</label>
                <input type="text" name={field.name} value={caseData[field.name]} onChange={handleChange}
                  className="w-full bg-zinc-900 border border-white/10 rounded-lg px-4 py-2 text-white text-sm outline-none focus:border-blue-500/50 transition-colors"/>
              </div>
            ))}
          </div>
          <div>
            <label className="text-gray-400 text-xs uppercase tracking-wider mb-1 block">Reason for claim</label>
            <textarea name="claim_reason" value={caseData.claim_reason} onChange={handleChange} rows={3}
              className="w-full bg-zinc-900 border border-white/10 rounded-lg px-4 py-2 text-white text-sm outline-none focus:border-blue-500/50 transition-colors resize-none"/>
          </div>
          {error&&<p className="text-red-400 text-sm">{error}</p>}
          <button onClick={handlePrepare} disabled={loading} className="btn-primary py-3 px-8 disabled:opacity-50">
            {loading?'Generating packet...':'Generate Filing Packet'}
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/30 text-green-300">✓ Filing packet generated. Follow the steps below.</div>
          {packet.instructions?.steps?.length>0&&(
            <div className="bg-zinc-800/30 border border-white/5 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">How to file</h3>
              <ol className="space-y-3 text-gray-300 text-sm">{packet.instructions.steps.map((step,i)=>(
                <li key={i} className="flex items-start gap-3">
                  <span className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5">{i+1}</span>{step}
                </li>
              ))}</ol>
            </div>
          )}
          {packet.button&&(
            <a href={packet.button.url} target="_blank" rel="noopener noreferrer" className="btn-primary flex items-center justify-center gap-2 py-3">
              <ExternalLink className="w-4 h-4"/>{packet.button.label_en||'File on MyFLCourtAccess'}
            </a>
          )}
          <button onClick={()=>setPacket(null)} className="btn-secondary py-2 px-6 text-sm">Edit case information</button>
        </div>
      )}
    </div>
  );
}

function ChatView({ documentId }) {
  const [messages, setMessages] = useState([]);
  const [inputVal, setInputVal] = useState('');
  const [sending, setSending] = useState(false);

  const handleSend = async () => {
    if (!inputVal.trim()||sending) return;
    const question = inputVal.trim(); setInputVal('');
    setMessages(prev=>[...prev,{role:'user',content:question}]); setSending(true);
    try {
      const res = await fetch(`${API_URL}/chat/${documentId}`,{
        method:'POST', headers:{'x-api-key':API_KEY,'Content-Type':'application/json'},
        body:JSON.stringify({question,lang:'en'})
      });
      if (!res.ok) throw new Error('Failed to get answer');
      const data = await res.json();
      setMessages(prev=>[...prev,{role:'ai',content:data.answer||'No answer returned.'}]);
    } catch(err) { setMessages(prev=>[...prev,{role:'ai',content:`Error: ${err.message}`}]); }
    finally { setSending(false); }
  };

  return (
    <div className="flex flex-col h-[500px] animate-slide-up">
      <div className="mb-6"><h2 className="text-3xl font-display font-bold mb-2">Ask LegalClear AI</h2><p className="text-gray-400">Ask any specific question about this document.</p></div>
      <div className="flex-1 rounded-xl p-2 overflow-y-auto space-y-6 mb-4">
        {messages.length===0&&<p className="text-gray-500 text-center text-sm mt-8">Ask a question about this document to get started.</p>}
        {messages.map((msg,idx)=>msg.role==='user'?(
          <div key={idx} className="flex gap-4 justify-end items-end">
            <div className="bg-zinc-800 text-gray-200 p-4 rounded-2xl rounded-tr-sm max-w-[80%] border border-white/5 shadow-md">{msg.content}</div>
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white text-xs font-bold shrink-0">JD</div>
          </div>
        ):(
          <div key={idx} className="flex gap-4 items-end">
            <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0 border border-white/10"><ShieldAlert className="w-4 h-4 text-white"/></div>
            <div className="bg-gradient-to-tr from-blue-600/10 to-indigo-500/10 border border-blue-500/20 p-5 rounded-2xl rounded-tl-sm max-w-[85%] shadow-md">
              <p className="text-gray-200 leading-relaxed whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}
        {sending&&<div className="flex gap-4 items-end"><div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0"><Loader2 className="w-4 h-4 text-white animate-spin"/></div><div className="bg-zinc-800/50 border border-white/5 p-4 rounded-2xl rounded-tl-sm"><p className="text-gray-400 text-sm">Thinking...</p></div></div>}
      </div>
      <div className="relative mt-2">
        <input type="text" value={inputVal} onChange={e=>setInputVal(e.target.value)} onKeyDown={e=>e.key==='Enter'&&handleSend()} placeholder="Ask a question about this document..." disabled={sending}
          className="w-full bg-zinc-900 border border-white/10 rounded-xl py-4 pl-5 pr-14 text-white outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all disabled:opacity-50"/>
        <button onClick={handleSend} disabled={sending} className="btn-primary absolute right-2 top-2 p-2 rounded-lg h-[calc(100%-16px)] w-10 flex cursor-pointer items-center justify-center disabled:opacity-50">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
        </button>
      </div>
    </div>
  );
}
