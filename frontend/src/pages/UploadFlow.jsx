import { UploadCloud, File, AlertCircle } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function UploadFlow() {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const navigate = useNavigate();

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsProcessing(true);
    
    try {
      const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8001";
      const arrayBuffer = await file.arrayBuffer();
      
      const uploadRes = await fetch(`${apiUrl}/upload`, {
        method: 'POST',
        headers: {
          'x-api-key': 'testkey123',
          'user-id': 'proto_user_001',
          'email': 'proto@example.com',
          'filename': encodeURIComponent(file.name),
          'lang': 'en',
          'Content-Type': 'application/octet-stream'
        },
        body: arrayBuffer
      });
      
      if (!uploadRes.ok) throw new Error("Upload failed: " + uploadRes.statusText);
      const uploadData = await uploadRes.json();
      
      if (uploadData.error) throw new Error(uploadData.message || "Upload failed");
      
      const sessionId = uploadData.session_id;
      if (sessionId) {
          const processRes = await fetch(`${apiUrl}/process/${sessionId}?lang=en`, {
            method: 'POST',
            headers: { 'x-api-key': 'testkey123' }
          });
          if (!processRes.ok) throw new Error("Processing logic failed or hit a context limit.");
      }
      
      setIsProcessing(false);
      navigate(`/results/${sessionId}`);
    } catch (err) {
      console.error(err);
      alert("Error analyzing file: " + err.message);
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen pt-24 px-4 sm:px-6 flex flex-col items-center">
      <div className="max-w-3xl w-full animate-slide-up">
        
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold mb-4">Upload Document</h1>
          <p className="text-gray-400">Supported formats: PDF, DOCX, TXT. Maximum file size: 10MB.</p>
        </div>

        <div className="glass-card p-1">
          <form 
            className={`relative rounded-xl border-2 border-dashed transition-all duration-300 p-12 flex flex-col items-center justify-center text-center ${dragActive ? 'border-primary bg-primary/5' : 'border-white/20 hover:border-primary/50 bg-white/5'}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input 
              type="file" 
              className="hidden" 
              id="file-upload" 
              onChange={handleChange}
              accept=".pdf,.docx,.txt"
            />
            
            {isProcessing ? (
              <div className="flex flex-col items-center space-y-6">
                <div className="relative w-20 h-20">
                  <div className="absolute inset-0 border-4 border-primary/30 rounded-full"></div>
                  <div className="absolute inset-0 border-4 border-primary rounded-full animate-[spin_1.5s_linear_infinite] border-t-transparent"></div>
                  <File className="absolute inset-0 m-auto h-8 w-8 text-primary animate-pulse" />
                </div>
                <div className="text-xl font-medium text-white">Analyzing Legal Text...</div>
                <p className="text-primary/80">Running AI Classifiers & Risk Scanners</p>
              </div>
            ) : file ? (
              <div className="flex flex-col items-center space-y-6">
                <div className="h-20 w-20 bg-primary/20 rounded-full flex items-center justify-center">
                  <File className="h-10 w-10 text-primary" />
                </div>
                <div>
                  <h3 className="text-xl font-medium text-white mb-2">{file.name}</h3>
                  <p className="text-gray-400 text-sm">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
                <div className="flex gap-4">
                  <button type="button" onClick={() => setFile(null)} className="btn-secondary py-2">
                    Cancel
                  </button>
                  <button type="button" onClick={handleUpload} className="btn-primary py-2 px-8">
                    Analyze Now
                  </button>
                </div>
              </div>
            ) : (
              <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center w-full h-full">
                <div className="h-20 w-20 bg-white/5 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <UploadCloud className="h-10 w-10 text-gray-400" />
                </div>
                <h3 className="text-xl font-medium text-white mb-2">Click to upload or drag and drop</h3>
                <p className="text-gray-400">Your documents are encrypted and kept strictly confidential.</p>
              </label>
            )}
          </form>
        </div>

        <div className="mt-8 flex items-start gap-3 p-4 bg-yellow-500/10 rounded-xl border border-yellow-500/20 text-sm text-gray-300">
          <AlertCircle className="w-5 h-5 text-yellow-500 shrink-0" />
          <p>LegalClear provides AI-generated explanations and risk scans. It does not constitute formal legal advice. Always consult with a qualified attorney for serious legal matters.</p>
        </div>

      </div>
    </div>
  );
}
