import React, { useState, useEffect, useRef, useMemo } from 'react';
import axios from 'axios';
import JsSIP from 'jssip';
import { Phone, User, Activity, LogOut, CheckCircle, XCircle, X, Save, FileText, Mail, ShieldCheck, PhoneCall, Loader2, Play, Volume2, Search, PhoneForwarded, BarChart3, TrendingUp, PhoneMissed, Lock, ShieldAlert, ClipboardCheck, AlertTriangle, Sun, Moon, PhoneOff, Timer } from 'lucide-react';

// تنظیم هدرهای پیش‌فرض اکسپورت فرکانس‌های میان‌سایتی به بک‌اند جنگو
axios.defaults.baseURL = 'http://127.0.0.1:8000';
axios.defaults.withCredentials = true; // اجبار پاس‌دادن کوکی‌های امنیتی سشن

// ============================================================================
// 🚀 کامپوننت اختصاصی لیست تماس‌ها جهت افزایش سرعت اسکرول و رندر فرانت‌اِند
// ============================================================================
const CallListSection = React.memo(({ title, icon, badgeColor, calls, dialingPhone, selectedPhone, isDarkMode, onDial, onLoadAudio, onOpenDrawer }) => {
  const textPrimary = isDarkMode ? "text-white" : "text-gray-900";
  const textSecondary = isDarkMode ? "text-gray-400" : "text-gray-600";

  return (
    <div style={{ contain: 'content' }} className={`p-4 sm:p-5 rounded-xl shadow-lg transition-colors duration-300 ${isDarkMode ? "bg-gray-900/95 border border-white/10" : "bg-white border border-gray-200/80"}`}>
      <h2 className={`text-base sm:text-lg font-black flex items-center justify-between mb-4 border-b pb-3 ${isDarkMode ? 'border-white/10 text-white' : 'border-gray-200 text-gray-900'}`}>
        <span className="flex items-center gap-2">
          <span className={badgeColor}>{icon}</span> {title}
        </span>
        <span className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${isDarkMode ? 'bg-gray-800 text-gray-400' : 'bg-slate-200 text-gray-600'}`}>
          {calls.length} مورد
        </span>
      </h2>
      
      <div className="space-y-2 max-h-[500px] overflow-y-auto pl-1 select-none custom-scrollbar">
        {calls.map(call => (
          <div 
            key={call.id} 
            onClick={() => onOpenDrawer(call.other_phone, call.is_agent)}
            className={`flex flex-col sm:flex-row justify-between items-start sm:items-center p-3 rounded-lg border cursor-pointer gap-3 transition-all duration-200 will-change-transform ${
              isDarkMode ? 'bg-gray-950/40 border-white/5 hover:border-gray-700' : 'bg-white/80 border-gray-200 hover:border-gray-400'
            } ${selectedPhone === call.other_phone ? 'border-red-500 bg-red-500/5' : ''}`}
          >
            <div className="flex items-center gap-3 w-full sm:w-auto">
              <button 
                onClick={(e) => { e.stopPropagation(); onDial(call.other_phone); }} 
                disabled={dialingPhone !== null} 
                className="p-2 rounded-lg border flex-shrink-0 transition-colors bg-green-500/10 text-green-500 border-green-500/30 hover:bg-green-500 hover:text-white"
              >
                <PhoneCall className="h-3.5 w-3.5" />
              </button>
              <div className="truncate">
                <div className="flex items-center gap-2">
                  <p className={`font-bold truncate text-sm sm:text-base ${textPrimary}`}>{call.display_name}</p>
                  {call.is_agent && <span className="text-[9px] bg-blue-500/10 text-blue-500 border border-blue-500/30 px-1.5 py-0.5 rounded font-bold tracking-wider">تیم</span>}
                </div>
                <p className={`text-xs mt-0.5 ${textSecondary}`}>شماره: <span className="font-mono">{call.other_phone}</span> • <span className="font-mono">{call.call_time}</span></p>
              </div>
            </div>
            <div className="flex items-center justify-between sm:justify-end gap-3 w-full sm:w-auto border-t sm:border-t-0 border-gray-800/20 pt-2 sm:pt-0">
              <span className={`text-xs font-mono ${textSecondary}`}>{call.duration}</span>
              {call.disposition === 'ANSWERED' && (
                <button 
                  onClick={(e) => { e.stopPropagation(); onLoadAudio(call.id, call.display_name); }} 
                  className={`p-1.5 rounded-md border text-xs flex items-center gap-1 font-bold transition-all ${isDarkMode ? 'bg-gray-800 text-gray-300 border-gray-700 hover:bg-gray-700 hover:text-white' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-100'}`}
                >
                  <Play className="h-3 w-3 fill-current" /> پخش
                </button>
              )}
              <span className={`text-[11px] px-2 py-1 rounded font-bold whitespace-nowrap ${call.disposition === 'ANSWERED' ? 'bg-green-500/10 text-green-500 border border-green-500/20' : 'bg-red-500/10 text-red-500 border border-red-500/20'}`}>
                {call.disposition === 'ANSWERED' ? 'پاسخ داده شده' : 'بدون پاسخ'}
              </span>
            </div>
          </div>
        ))}
        {calls.length === 0 && <p className="text-sm text-center py-12 text-gray-500">هیچ رکوردی یافت نشد.</p>}
      </div>
    </div>
  );
});

// ============================================================================
// 🚀 ارتقا پاپ‌آپ: بنر یکپارچه مدیریت وضعیت شماره‌گیری خروجی و مکالمه فعال وب‌آرتی‌سی
// ============================================================================
function ActiveCallBanner({ session, sipCallState, isCallOnHold, onToggleHold, onDecline }) {
  const [duration, setCallDuration] = useState(0);
  const isConnected = sipCallState === 'CONNECTED';

  useEffect(() => {
    if (!isConnected) return;
    setCallDuration(0);
    const interval = setInterval(() => {
      setCallDuration((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [session, isConnected]);

  const formatTime = (totalSeconds) => {
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className={`fixed top-24 left-1/2 transform -translate-x-1/2 border text-xs py-2 px-6 rounded-full font-black flex items-center justify-between gap-4 shadow-xl z-40 animate-fadeIn will-change-transform ${
      isConnected 
        ? 'bg-gray-900 border-green-500/30 text-green-400' 
        : 'bg-gray-900 border-amber-500/40 text-amber-400 animate-pulse'
    }`}>
      <div className="flex items-center gap-3">
        {isConnected ? (
          <Activity className="h-3.5 w-3.5 animate-spin text-green-400" />
        ) : (
          <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-400" />
        )}
        <span>
          {isConnected ? 'مکالمه زنده برقرار است' : 'در حال شماره‌گیری و تماس...'} • شماره: <strong className="font-mono">{session.remote_identity.uri.user}</strong>
        </span>
      </div>

      {isConnected && (
        <div className="flex items-center gap-1 bg-green-500/20 text-green-300 font-mono font-bold px-2 py-0.5 rounded-md border border-green-500/30">
          <Timer className="h-3 w-3 text-green-400" />
          <span>{formatTime(duration)}</span>
        </div>
      )}

      <div className="flex items-center gap-2 border-r border-gray-500/20 pr-2">
        {isConnected && (
          <button
            onClick={onToggleHold}
            className={`text-[10px] font-bold px-2.5 py-1 rounded transition-all cursor-pointer ${isCallOnHold ? 'bg-amber-600 text-white animate-pulse' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'}`}
          >
            {isCallOnHold ? 'وصل مجدد (Unhold)' : 'انتظار (Hold)'}
          </button>
        )}
        <button 
          onClick={onDecline}
          className="bg-red-600 hover:bg-red-700 text-white font-bold rounded-full p-1 transition-all cursor-pointer"
          title={isConnected ? "قطع مکالمه" : "لغو تماس خروجی"}
        >
          <X className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// 🏛️ بدنه اصلی کنترلر کارتابل
// ============================================================================
export default function App() {
  const [authLoading, setAuthLoading] = useState(true); 
  const [isAuthenticated, setIsAuthenticated] = useState(false); 
  const [loading, setLoading] = useState(true);
  const [agentData, setAgentData] = useState(null);
  const [activeCall, setActiveCall] = useState(null);

  const [isDarkMode, setIsDarkMode] = useState(true);

  // حالت‌های موتور مخابراتی
  const [sipRegistered, setSipRegistered] = useState(false);
  const [sipCallState, setSipCallState] = useState('IDLE'); 
  const [activeSipSession, setActiveSipSession] = useState(null);
  const [isCallOnHold, setIsCallOnHold] = useState(false); 
  const [sipError, setSipError] = useState('');
  
  // دکمه فرکانس سینک بی‌صدا دیتابیس
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const uaRef = useRef(null);
  const currentSessionRef = useRef(null);

  // 🔧 Unmount cleanup — prevents SSL error on page refresh
  useEffect(() => {
    return () => {
      if (uaRef.current) {
        try {
          uaRef.current.unregister({ all: true });
          uaRef.current.stop();
        } catch (e) {}
        uaRef.current = null;
      }
    };
  }, []);

  // فیلدهای فرم کارتابل کارشناس
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [wrapupData, setWrapupData] = useState(null); 
  const [wrapupForm, setWrapupForm] = useState({ disposition: '', notes: '' });
  const [isSubmittingWrapup, setIsSubmittingWrapup] = useState(false);
  const [wrapupError, setWrapupError] = useState('');

  const [selectedPhone, setSelectedPhone] = useState(null);
  const [isAgentProfile, setIsAgentProfile] = useState(false); 
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [customerForm, setCustomerForm] = useState({ first_name: '', last_name: '', email: '', notes: '' });
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null); 

  const [dialingPhone, setDialingPhone] = useState(null);
  const [manualNumber, setManualNumber] = useState(''); 
  const [currentAudio, setCurrentAudio] = useState(null); 
  const [searchQuery, setSearchQuery] = useState(''); 

  // پالت رنگی رابط کاربری شیشه‌ای هوشمند
  const glassClass = isDarkMode 
    ? "bg-gray-900/95 border border-white/10 shadow-2xl" 
    : "bg-white border border-gray-200/90 shadow-xl";

  const innerGlassClass = isDarkMode ? "bg-gray-950/80 border border-white/5" : "bg-gray-50 border border-gray-200/60";
  const textPrimary = isDarkMode ? "text-white" : "text-gray-900";
  const textSecondary = isDarkMode ? "text-gray-400" : "text-gray-600";
  const textMuted = isDarkMode ? "text-gray-500" : "text-gray-400";
  const inputBg = isDarkMode ? "bg-gray-950/80 focus:border-red-500" : "bg-white focus:border-red-600 shadow-inner";

  useEffect(() => {
    axios.get('/api/auth/status/')
      .then(res => {
        if (res.data.authenticated) {
          setIsAuthenticated(true);
          fetchDashboardData(false); 
        }
        setAuthLoading(false);
      })
      .catch(() => {
        setIsAuthenticated(false);
        setAuthLoading(false);
      });
  }, []);

  useEffect(() => {
    if (refreshTrigger > 0) {
      fetchDashboardData(true); 
    }
  }, [refreshTrigger]);

  const fetchDashboardData = (silent = false) => {
    if (!silent) setLoading(true);
    axios.get('/api/dashboard/data/')
      .then(res => {
        setAgentData(res.data);
        setLoading(false);
        if (
          res.data.extension_number &&
          res.data.extension_number !== "Not Assigned" &&
          res.data.extension_secret &&
          !uaRef.current  // 🔧 only init if UA doesn't exist yet
        ) {
          initializeWebRTC(res.data.extension_number, res.data.extension_secret);
        }
      })
      .catch(err => {
        console.error("API error:", err);
        setLoading(false);
      });
  };

  const handleWrapupFormSubmit = (e) => {
    e.preventDefault();
    setIsSubmittingWrapup(true);
    setWrapupError('');

    axios.post('/api/call/wrapup/save/', {
      phone_number: wrapupData.phone_number,
      disposition: wrapupForm.disposition,
      notes: wrapupForm.notes,
    })
      .then(() => {
        setWrapupData(null);
        setIsSubmittingWrapup(false);
        setRefreshTrigger(prev => prev + 1);
      })
      .catch(err => {
        setWrapupError(err.response?.data?.message || 'خطا در ثبت اطلاعات. دوباره تلاش کنید.');
        setIsSubmittingWrapup(false);
      });
  };

  const initializeWebRTC = (extension, secret) => {
    const webrtcExtension = `8${extension}`;
    console.log(`🔌 Initializing WebRTC PJSIP Engine for extension: ${webrtcExtension}`);

    // 🔧 Clean up any existing UA properly before creating a new one
    if (uaRef.current) {
      try {
        uaRef.current.unregister({ all: true });
      } catch (e) {}
      setTimeout(() => {
        try { uaRef.current.stop(); } catch (e) {}
        uaRef.current = null;
        _startUA(webrtcExtension, secret);
      }, 500);
      return;
    }

    _startUA(webrtcExtension, secret);
  };

  const _startUA = (webrtcExtension, secret) => {
    const socket = new JsSIP.WebSocketInterface('wss://192.168.100.115:8089/ws');

    const config = {
      sockets: [socket],
      uri: `sip:${webrtcExtension}@192.168.100.115`,
      authorization_user: webrtcExtension,
      password: secret,
      register: true,
      session_timers: false,
      realm: 'asterisk',
      register_expires: 30,                  // short expiry → stale contacts die fast
      connection_recovery_min_interval: 2,
      connection_recovery_max_interval: 10,
      no_answer_timeout: 60,
    };

    const ua = new JsSIP.UA(config);
    uaRef.current = ua;

    // ── Registration events ──────────────────────────────────────────
    ua.on('registered', () => {
      console.log('✅ SIP Registered');
      setSipRegistered(true);
      setSipError('');
    });

    ua.on('unregistered', () => {
      console.warn('⚠️ SIP Unregistered');
      setSipRegistered(false);
    });

    ua.on('registrationFailed', (e) => {
      console.error('❌ Registration failed:', e.cause);
      setSipRegistered(false);
      setSipError(`خطا در اتصال تلفن داخلی: ${e.cause}`);
    });

    // 🔧 WebSocket dropped silently → re-register when it comes back
    ua.on('disconnected', () => {
      console.warn('🔌 WebSocket disconnected');
      setSipRegistered(false);
    });

    ua.on('connected', () => {
      console.log('🔌 WebSocket connected');
    });

    // ── Incoming / Outgoing calls ────────────────────────────────────
    ua.on('newRTCSession', (data) => {
      const session = data.session;

      // 🔧 Terminate any ghost session before accepting the new one
      if (currentSessionRef.current && currentSessionRef.current !== session) {
        try { currentSessionRef.current.terminate(); } catch (e) {}
        currentSessionRef.current = null;
      }

      currentSessionRef.current = session;
      setActiveSipSession(session);
      setIsCallOnHold(false);

      if (session.direction === 'incoming') {
        console.log('📞 Incoming call from:', session.remote_identity.uri.user);
        setSipCallState('RINGING');
        setActiveCall({
          caller: session.remote_identity.display_name || session.remote_identity.uri.user,
          number: session.remote_identity.uri.user,
        });
      } else {
        console.log('📤 Outgoing call to:', session.remote_identity.uri.user);
      }

      // 🔧 'confirmed' is more reliable than 'accepted' for knowing the call is live
      session.on('confirmed', () => {
        console.log('✅ Call confirmed/connected');
        setSipCallState('CONNECTED');
        setActiveCall(null);
      });

      session.on('accepted', () => {
        setSipCallState('CONNECTED');
        setActiveCall(null);
      });

      session.on('hold', () => {
        console.log('⏸ Call on hold');
        setIsCallOnHold(true);
      });

      session.on('unhold', () => {
        console.log('▶️ Call resumed');
        setIsCallOnHold(false);
      });

      session.on('ended', (e) => {
        console.log('📵 Call ended:', e.cause);
        handleCallCleanup();
        setTimeout(() => setRefreshTrigger(prev => prev + 1), 2200);
      });

      session.on('failed', (e) => {
        console.warn('❌ Call failed:', e.cause);

        // 🔧 CANCEL = softphone answered via Follow Me, not a real error
        if (e.cause === JsSIP.C.causes.CANCELED) {
          console.log('ℹ️ Call canceled (Follow Me resolved elsewhere)');
          handleCallCleanup();
          return;
        }

        handleCallCleanup();
        setTimeout(() => setRefreshTrigger(prev => prev + 1), 2200);
      });

      // 🔧 Remote audio — handles both 'track' (modern) and 'addstream' (fallback)
      session.on('peerconnection', (pcData) => {
        const pc = pcData.peerconnection;

        pc.addEventListener('track', (e) => {
          console.log('🔊 Remote audio track received');
          const remoteAudio = document.getElementById('webRtcRemoteAudio');
          if (remoteAudio && e.streams[0]) {
            remoteAudio.srcObject = e.streams[0];
            remoteAudio.play().catch(err => console.warn('Audio play blocked:', err));
          }
        });

        pc.addEventListener('addstream', (e) => {
          const remoteAudio = document.getElementById('webRtcRemoteAudio');
          if (remoteAudio && e.stream) {
            remoteAudio.srcObject = e.stream;
          }
        });
      });
    });

    ua.start();
  };

  const handleCallCleanup = () => {
    setSipCallState('IDLE');
    setActiveSipSession(null);
    currentSessionRef.current = null;
    setActiveCall(null);
    setIsCallOnHold(false);

    // 🔧 Re-register if UA lost registration during the call
    setTimeout(() => {
      if (uaRef.current && !uaRef.current.isRegistered()) {
        console.warn('⚠️ UA lost registration after cleanup — re-registering');
        uaRef.current.register();
      }
    }, 500);
  };

  const handleNativeSipAnswer = () => {
    if (currentSessionRef.current && sipCallState === 'RINGING') {
      currentSessionRef.current.answer({ mediaConstraints: { audio: true, video: false } });
    }
  };

  const handleNativeSipDecline = () => {
    if (currentSessionRef.current) {
      currentSessionRef.current.terminate();
      handleCallCleanup();
    }
  };

  const handleToggleHold = () => {
    if (currentSessionRef.current && sipCallState === 'CONNECTED') {
      if (currentSessionRef.current.isOnHold().local) {
        currentSessionRef.current.unhold();
      } else {
        currentSessionRef.current.hold();
      }
    }
  };

  useEffect(() => {
    if (!isAuthenticated) return; 
    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const socket = new WebSocket(`${protocol}127.0.0.1:8000/ws/calls/`);
    
    socket.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'clear_notification') {
        if (sipCallState === 'IDLE') setActiveCall(null);
        setRefreshTrigger(prev => prev + 1);
      } else if (data.type === 'show_wrapup') {
        setActiveCall(null); 
        setWrapupForm({ disposition: '', notes: '' }); 
        setWrapupError('');
        setWrapupData({ phone_number: data.phone_number, caller_name: data.caller_name || 'مشتری خارجی' });
      }
    };
    return () => socket.close();
  }, [isAuthenticated, sipCallState]);

  useEffect(() => {
    if (!selectedPhone) return;
    setDrawerLoading(true);
    setSaveStatus(null);
    
    if (isAgentProfile) {
      const allLogs = [...(agentData?.inbound_calls || []), ...(agentData?.outbound_calls || [])];
      const matchedLog = allLogs.find(c => c.other_phone === selectedPhone);
      setCustomerForm({
        first_name: matchedLog?.display_name || 'خط داخلی سیستم',
        last_name: 'پروفایل همکار',
        email: 'شبکه تلفنی درون‌سازمانی',
        notes: 'این داخلی به عنوان یک دارایی در دفترچه تلفن مرکزی سازمان ثبت شده است.'
      });
      setDrawerLoading(false);
      return;
    }

    axios.get(`/call/customer/lookup/${selectedPhone}/`)
      .then(res => {
        setCustomerForm({ first_name: res.data.first_name || '', last_name: res.data.last_name || '', email: res.data.email || '', notes: res.data.notes || '' });
        setDrawerLoading(false);
      })
      .catch(() => setDrawerLoading(false));
  }, [selectedPhone, isAgentProfile, agentData]);

  const handleInitializeDial = (phoneNumber) => {
    if (!phoneNumber) return;
    const sanitizedNumber = phoneNumber.replace(/\s+/g, '');
    setDialingPhone(sanitizedNumber);

    if (sipRegistered && uaRef.current) {
      const agentDisplayName = agentData?.agent_name || 'Agent';
      const technicalExtension = agentData?.extension_number || '101';
      const options = {
        mediaConstraints: { audio: true, video: false },
        rtcOfferConstraints: { offerToReceiveAudio: 1, offerToReceiveVideo: 0 },
        extraHeaders: [
          `P-Asserted-Identity: "${agentDisplayName}" <sip:${technicalExtension}@192.168.100.115>`,
          `Remote-Party-ID: "${agentDisplayName}" <sip:${technicalExtension}@192.168.100.115>;party=calling;screen=yes;privacy=off`
        ]
      };
      const session = uaRef.current.call(`sip:${sanitizedNumber}@192.168.100.115`, options);
      currentSessionRef.current = session;
      setActiveSipSession(session);
      
      // فعال‌سازی فوری وضعیت شماره‌گیری برای رندر گرفتن بنر بالایی
      setSipCallState('RINGING'); 
      
      setTimeout(() => setDialingPhone(null), 1000);
      return;
    }

    axios.get(`/call/dial/${sanitizedNumber}/`)
      .then(() => setTimeout(() => setDialingPhone(null), 2500))
      .catch(() => setDialingPhone(null));
  };

  const handleSaveCustomer = (e) => {
    e.preventDefault();
    if (isAgentProfile) return; 
    setIsSaving(true);
    setSaveStatus(null);
    axios.post('/call/customer/save/', {
      phone_number: selectedPhone,
      first_name: customerForm.first_name,
      last_name: customerForm.last_name,
      email: customerForm.email,
      notes: customerForm.notes
    }).then(() => {
        setIsSaving(false);
        setSaveStatus('success');
        setRefreshTrigger(prev => prev + 1); 
        setTimeout(() => setSaveStatus(null), 3000);
      }).catch(() => {
        setIsSaving(false);
        setSaveStatus('error');
      });
  };

  const handleLoginSubmit = (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setAuthError('');

    axios.post('/api/auth/login/', { username, password })
      .then(() => {
        setIsAuthenticated(true);
        fetchDashboardData(false); 
        setIsSubmitting(false);
      })
      .catch(err => {
        setAuthError(err.response?.data?.message || 'نام کاربری یا رمز عبور اشتباه است.');
        setIsSubmitting(false);
      });
  };

  const handleLogoutAction = () => {
    axios.get('/api/auth/logout/')
      .then(() => {
        setIsAuthenticated(false);
        setAgentData(null);
        setCurrentAudio(null);
        setSelectedPhone(null);
        if (uaRef.current) {
          try {
            uaRef.current.unregister({ all: true });
            uaRef.current.stop();
          } catch (e) {}
          uaRef.current = null;
        }
        setSipRegistered(false);
      })
      .catch(err => console.error("Error breaking session validation path:", err));
  };

  const handleManualCallSubmit = (e) => {
    e.preventDefault();
    if (!manualNumber) return;
    handleInitializeDial(manualNumber);
    setManualNumber(''); 
  };

  const handleLoadAudio = (logId, displayName) => {
    setCurrentAudio({ id: logId, name: displayName, url: `http://127.0.0.1:8000/call/play/${logId}/` });
  };

  const triggerDrawerOpening = (phoneNum, isAgentCheck) => {
    setIsAgentProfile(isAgentCheck);
    setSelectedPhone(phoneNum);
  };

  // ============================================================================
  // ⚡ لایه کش اختصاصی رندرینگ
  // ============================================================================
  const stats = useMemo(() => {
    const inbound = agentData?.inbound_calls || [];
    const outbound = agentData?.outbound_calls || [];
    const combined = [...inbound, ...outbound];
    const total = combined.length;
    const answered = combined.filter(c => c.disposition === 'ANSWERED').length;
    return {
      totalCallsCount: total, answeredCount: answered, missedCount: total - answered, successRatio: total > 0 ? Math.round((answered / total) * 100) : 0
    };
  }, [agentData]);

  const filteredInbound = useMemo(() => {
    return (agentData?.inbound_calls || []).filter(call => 
      call.display_name.toLowerCase().includes(searchQuery.toLowerCase()) || call.other_phone.includes(searchQuery)
    );
  }, [agentData?.inbound_calls, searchQuery]);

  const filteredOutbound = useMemo(() => {
    return (agentData?.outbound_calls || []).filter(call => 
      call.display_name.toLowerCase().includes(searchQuery.toLowerCase()) || call.other_phone.includes(searchQuery)
    );
  }, [agentData?.outbound_calls, searchQuery]);

  if (authLoading) {
    return (
      <div className={`flex h-screen w-screen items-center justify-center ${isDarkMode ? 'bg-gray-950 text-gray-100' : 'bg-slate-100 text-gray-800'}`} dir="rtl">
        <div className="text-center px-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-red-500 border-t-transparent mx-auto"></div>
          <p className={`mt-4 font-medium text-sm ${textSecondary}`}>در حال بررسی نشست‌های امنیتی...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className={`min-h-screen w-full flex items-center justify-center p-4 ${isDarkMode ? 'bg-gradient-to-br from-gray-950 via-slate-900 to-zinc-950' : 'bg-gradient-to-br from-slate-100 via-zinc-200 to-gray-300'}`} dir="rtl">
        <div className={`w-full max-w-md p-6 rounded-2xl relative overflow-hidden ${glassClass}`}>
          <div className="absolute top-0 right-0 w-full h-1.5 bg-gradient-to-l from-red-500 to-red-800"></div>
          <div className="text-center mb-6">
            <div className={`h-11 w-11 rounded-xl flex items-center justify-center mx-auto mb-4 border ${isDarkMode ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-red-100 text-red-600 border-red-200'}`}><Lock className="h-5 w-5" /></div>
            <h2 className={`text-xl font-black ${textPrimary}`}>احراز هویت ورود به سیستم</h2>
          </div>
          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <div><label className={`block text-xs font-bold mb-2 ${textSecondary}`}>نام کاربری</label><input type="text" required value={username} onChange={e => setUsername(e.target.value)} className={`w-full border border-gray-700/60 rounded-lg p-3 text-sm focus:outline-none ${inputBg} ${textPrimary}`} placeholder="username" /></div>
            <div><label className={`block text-xs font-bold mb-2 ${textSecondary}`}>رمز عبور</label><input type="password" required value={password} onChange={e => setPassword(e.target.value)} className={`w-full border border-gray-700/60 rounded-lg p-3 text-sm focus:outline-none ${inputBg} ${textPrimary}`} placeholder="••••••••••••" /></div>
            {authError && <div className="bg-red-950/40 border border-red-900 text-red-400 text-xs p-3 rounded-lg flex items-center gap-2"><ShieldAlert className="h-4 w-4" /> {authError}</div>}
            <button type="submit" disabled={isSubmitting} className="w-full bg-red-500 hover:bg-red-600 text-white font-bold text-sm p-3 rounded-lg transition">{isSubmitting ? 'در حال ورود...' : 'ورود به سیستم'}</button>
          </form>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={`flex h-screen w-screen items-center justify-center ${isDarkMode ? 'bg-gray-950 text-gray-100' : 'bg-slate-100 text-gray-800'}`} dir="rtl">
        <div className="text-center px-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-red-500 border-t-transparent mx-auto"></div>
          <p className={`mt-4 font-medium text-sm ${textSecondary}`}>در حال راه‌اندازی زیرساخت صوتی...</p>
        </div>
      </div>
    );
  }

  return (
    <>
    <audio id="webRtcRemoteAudio" autoPlay style={{ display: 'none' }} />
    <div className={`min-h-screen p-3 sm:p-6 relative overflow-x-hidden pb-40 transition-all duration-500 ${isDarkMode ? 'bg-gradient-to-br from-gray-950 via-slate-900 to-zinc-950 text-gray-100' : 'bg-gradient-to-br from-slate-50 via-zinc-100 to-gray-200 text-gray-800'}`} dir="rtl">      
      <div className={`transition-all duration-300 ease-in-out will-change-[padding] ${selectedPhone ? 'xl:pl-96' : ''} ${wrapupData ? 'blur-sm pointer-events-none' : ''}`}>
        <header className="flex flex-col md:flex-row gap-4 justify-between items-center p-4 rounded-xl mb-6 border border-white/10 shadow-2xl glass-card">
          <div className="flex items-center gap-3">
            <div className={`h-3 w-3 rounded-full animate-pulse ${sipRegistered ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <h1 className={`text-lg sm:text-xl font-black ${textPrimary}`}>داشبورد سی‌آر‌ام <span className="text-red-500">ایزابل</span></h1>
          </div>
          <div className="flex flex-wrap items-center justify-center md:justify-end gap-3 text-xs sm:text-sm font-semibold w-full md:w-auto">
            <button onClick={() => setIsDarkMode(!isDarkMode)} className={`p-2 rounded-md border transition-all flex items-center justify-center shadow-sm cursor-pointer ${isDarkMode ? 'bg-gray-800 text-yellow-400 border-gray-700 hover:bg-gray-700' : 'bg-white text-indigo-600 border-gray-300 hover:bg-gray-100'}`}>{isDarkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}</button>
            <span className={`px-3 py-1.5 rounded-md border ${innerGlassClass} ${textSecondary}`}>کارشناس: <strong className={textPrimary}>{agentData?.agent_name}</strong></span>
            <span className={`px-3 py-1.5 rounded-md border ${innerGlassClass} ${textSecondary}`}>داخلی: <strong className="text-red-500 font-mono">{agentData?.extension_number}</strong></span>
            <button onClick={handleLogoutAction} className={`p-1.5 sm:p-2 border rounded-md transition flex items-center gap-1.5 cursor-pointer text-xs ${isDarkMode ? 'bg-gray-800 hover:bg-red-950 hover:text-red-400 text-gray-400 border-gray-700' : 'bg-white hover:bg-red-50 hover:text-red-600 text-gray-600 border-gray-300'}`}><LogOut className="h-3.5 w-3.5 transform rotate-180" /><span>خروج</span></button>
          </div>
        </header>

        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className={`p-4 rounded-xl flex items-center justify-between ${glassClass}`}><div><p className={`text-xs font-bold tracking-wider ${textSecondary}`}>کل تماس‌ها</p><h3 className={`text-2xl font-black mt-1 font-mono ${textPrimary}`}>{stats.totalCallsCount}</h3></div><div className={`p-3 rounded-lg ${isDarkMode ? 'bg-gray-800 text-gray-400' : 'bg-slate-200 text-gray-600'}`}><BarChart3 className="h-5 w-5" /></div></div>
          <div className={`p-4 rounded-xl flex items-center justify-between ${glassClass}`}><div><p className={`text-xs font-bold tracking-wider ${textSecondary}`}>پاسخ داده شده</p><h3 className="text-2xl font-black text-green-500 mt-1 font-mono">{stats.answeredCount}</h3></div><div className="p-3 bg-green-500/10 text-green-500 rounded-lg"><TrendingUp className="h-5 w-5" /></div></div>
          <div className={`p-4 rounded-xl flex items-center justify-between ${glassClass}`}><div><p className={`text-xs font-bold tracking-wider ${textSecondary}`}>از دست رفته</p><h3 className="text-2xl font-black text-red-500 mt-1 font-mono">{stats.missedCount}</h3></div><div className="p-3 bg-red-500/10 text-red-500 rounded-lg"><PhoneMissed className="h-5 w-5" /></div></div>
          <div className={`p-4 rounded-xl flex items-center justify-between ${glassClass}`}><div><p className={`text-xs font-bold tracking-wider ${textSecondary}`}>نرخ موفقیت</p><h3 className="text-2xl font-black text-blue-500 mt-1 font-mono">{stats.successRatio}%</h3></div><div className="p-3 bg-blue-500/10 text-blue-500 rounded-lg"><Activity className="h-5 w-5" /></div></div>
        </section>

        <section className={`p-4 rounded-xl mb-6 shadow-md flex flex-col md:flex-row gap-4 items-center justify-between ${glassClass}`}>
          <div className="relative w-full md:max-w-md">
            <Search className="absolute right-3.5 top-3.5 h-4 w-4 text-gray-500" />
            <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="جستجوی سوابق بر اساس نام یا شماره..." className={`w-full border border-gray-700/60 rounded-lg pr-10 pl-4 py-2.5 text-sm transition focus:outline-none ${inputBg} ${textPrimary}`} />
            {searchQuery && (<button onClick={() => setSearchQuery('')} className={`absolute left-3 top-3.5 hover:${textPrimary} ${textMuted}`}><X className="h-4 w-4" /></button>)}
          </div>
          <form onSubmit={handleManualCallSubmit} className="flex gap-2 w-full md:w-auto items-center justify-between">
            <input type="text" required value={manualNumber} onChange={e => setManualNumber(e.target.value.replace(/[^0-9]/g, ''))} placeholder="شماره‌گیری جدید..." className={`w-full md:w-56 border border-gray-700/60 rounded-lg px-3 py-2.5 text-sm font-mono transition text-left focus:outline-none ${inputBg} ${textPrimary}`} />
            <button type="submit" disabled={dialingPhone !== null || !manualNumber} className="px-4 py-2.5 bg-green-600 hover:bg-green-700 disabled:opacity-40 text-white font-bold text-sm rounded-lg shadow-md cursor-pointer"><PhoneForwarded className="h-4 w-4 transform rotate-180" />تماس</button>
          </form>
        </section>

        <main className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <CallListSection title="تماس‌های ورودی" icon="📥" badgeColor="text-green-400" calls={filteredInbound} dialingPhone={dialingPhone} selectedPhone={selectedPhone} isDarkMode={isDarkMode} onDial={handleInitializeDial} onLoadAudio={handleLoadAudio} onOpenDrawer={triggerDrawerOpening} />
          <CallListSection title="تماس‌های خروجی" icon="📤" badgeColor="text-blue-500" calls={filteredOutbound} dialingPhone={dialingPhone} selectedPhone={selectedPhone} isDarkMode={isDarkMode} onDial={handleInitializeDial} onLoadAudio={handleLoadAudio} onOpenDrawer={triggerDrawerOpening} />
        </main>
      </div>

      {/* کشوی متحرک اطلاعات مشتری */}
      <div style={{ contain: 'layout paint' }} className={`fixed top-0 left-0 h-full w-full max-w-md sm:w-96 border-r shadow-2xl p-6 transition-transform duration-300 ease-in-out z-40 will-change-transform ${glassClass} ${selectedPhone ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex flex-col h-full">
          <div className={`flex justify-between items-center border-b pb-4 mb-6 ${isDarkMode ? 'border-white/10' : 'border-gray-200'}`}>
            <div className="flex items-center gap-2"><User className="h-5 w-5 text-red-500" /><h3 className={`text-lg font-black ${textPrimary}`}>{isAgentProfile ? 'نود داخلی سیستم' : 'میز کار مشتری'}</h3></div>
            <button onClick={() => setSelectedPhone(null)} className={`p-1.5 rounded-lg border cursor-pointer ${isDarkMode ? 'bg-gray-800 border-gray-700 text-gray-400' : 'bg-white border-gray-300 text-gray-500'}`}><X className="h-4 w-4" /></button>
          </div>
          {drawerLoading ? (
            <div className="flex-1 flex items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-2 border-red-500 border-t-transparent"></div></div>
          ) : (
            <form onSubmit={handleSaveCustomer} className="flex-1 flex flex-col justify-between overflow-y-auto pr-1 custom-scrollbar">
              <div className="space-y-4">
                <div className={`border p-3 rounded-lg flex items-center justify-between gap-3 mb-2 ${isAgentProfile ? 'bg-blue-500/10 border-blue-500/20' : 'bg-gray-950/20 border-gray-800/40'}`}>
                  <div className="flex items-center gap-3">
                    <Phone className={`h-4 w-4 ${isAgentProfile ? 'text-blue-500' : 'text-green-500'}`} />
                    <div><p className={`text-xs font-bold uppercase tracking-wider ${textMuted}`}>شماره ارتباطی</p><p className={`text-sm font-mono font-bold text-left ${textPrimary}`}>{selectedPhone}</p></div>
                  </div>
                  <button type="button" disabled={dialingPhone !== null} onClick={() => handleInitializeDial(selectedPhone)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold border border-green-500/30 bg-green-500/10 text-green-500 hover:bg-green-500"><PhoneCall className="h-3 w-3" />تماس</button>
                </div>
                {!isAgentProfile && (
                  <>
                    <div><label className={`block text-xs font-bold uppercase mb-2 ${textSecondary}`}>نام</label><input type="text" required value={customerForm.first_name} onChange={e => setCustomerForm({ ...customerForm, first_name: e.target.value })} className={`w-full border border-gray-700/60 rounded-lg p-2.5 text-sm focus:outline-none ${inputBg} ${textPrimary}`} placeholder="محمد" /></div>
                    <div><label className={`block text-xs font-bold uppercase mb-2 ${textSecondary}`}>نام خانوادگی</label><input type="text" value={customerForm.last_name} onChange={e => setCustomerForm({ ...customerForm, last_name: e.target.value })} className={`w-full border border-gray-700/60 rounded-lg p-2.5 text-sm focus:outline-none ${inputBg} ${textPrimary}`} placeholder="منصوری" /></div>
                    <div><label className={`block text-xs font-bold uppercase mb-2 ${textSecondary}`}>آدرس ایمیل</label><div className="relative"><Mail className="absolute right-3 top-3.5 h-4 w-4 text-gray-500" /><input type="email" value={customerForm.email} onChange={e => setCustomerForm({ ...customerForm, email: e.target.value })} className={`w-full border border-gray-700/60 rounded-lg p-2.5 pr-10 text-sm font-mono focus:outline-none ${inputBg} ${textPrimary}`} placeholder="name@company.com" /></div></div>
                    <div><label className={`block text-xs font-bold uppercase mb-2 ${textSecondary}`}>یادداشت‌های عملیاتی</label><div className="relative"><FileText className="absolute right-3 top-3.5 h-4 w-4 text-gray-500" /><textarea value={customerForm.notes} onChange={e => setCustomerForm({ ...customerForm, notes: e.target.value })} rows="4" className={`w-full border border-gray-700/60 rounded-lg p-2.5 pr-10 text-sm transition resize-none focus:outline-none ${inputBg} ${textPrimary}`} placeholder="جزئیات تعاملات..."></textarea></div></div>
                  </>
                )}
              </div>
              {!isAgentProfile && <button type="submit" disabled={isSaving} className="w-full bg-red-500 hover:bg-red-600 text-white font-bold text-sm p-3 rounded-lg flex items-center justify-center gap-2 transition cursor-pointer"><Save className="h-4 w-4" />{isSaving ? 'در حال ذخیره‌سازی...' : 'ذخیره کارت مشتری'}</button>}
            </form>
          )}
        </div>
      </div>

      {/* پاپ‌آپ هوشمند تماس ورودی وب‌آرتی‌سی */}
      {activeCall && sipCallState === 'RINGING' && (
        <div className={`fixed bottom-4 left-4 right-4 sm:left-auto sm:right-6 sm:bottom-6 w-auto sm:w-80 border-r-8 rounded-xl p-4 sm:p-5 z-50 shadow-2xl will-change-transform ${glassClass} border-amber-500 animate-pulse`}>
          <div className="flex items-start gap-4">
            <div className="p-2.5 sm:p-3 rounded-lg bg-amber-500/10 text-amber-400"><Phone className="h-5 w-5" /></div>
            <div className="flex-1 min-w-0">
              <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400">تماس ورودی زنده (WebRTC)...</h4>
              <h3 className={`text-lg sm:text-xl font-black mt-1 truncate ${textPrimary}`}>{activeCall.caller}</h3>
              <p className={`text-xs mt-0.5 ${textSecondary}`}>خط: <span className="font-mono">{activeCall.number}</span></p>
              <div className="flex gap-2 mt-4">
                <button onClick={handleNativeSipAnswer} className="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold text-xs py-2 px-3 rounded-md flex items-center justify-center gap-1 transition shadow-md cursor-pointer"><PhoneCall className="h-3 w-3" /> پاسخ تماس</button>
                <button onClick={handleNativeSipDecline} className="flex-1 bg-red-600 hover:bg-red-700 text-white font-bold text-xs py-2 px-3 rounded-md flex items-center justify-center gap-1 transition shadow-md cursor-pointer"><PhoneOff className="h-3 w-3" /> رد تماس</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ⚡ OPTIMIZATION: رندر گرفتن از بنر لایو برای هر دو وضعیت شماره‌گیری خروجی و مکالمه متصل شده فعال */}
      {((sipCallState === 'CONNECTED' || (sipCallState === 'RINGING' && activeSipSession?.direction === 'outgoing')) && activeSipSession) && (
        <ActiveCallBanner 
          session={activeSipSession} 
          sipCallState={sipCallState}
          isCallOnHold={isCallOnHold} 
          onToggleHold={handleToggleHold} 
          onDecline={handleNativeSipDecline} 
        />
      )}

      {/* پلیر صوتی ضبط مکالمات */}
      {currentAudio && (
        <div style={{ contain: 'layout paint' }} className={`fixed bottom-0 left-0 right-0 w-full border-t px-4 py-3 sm:px-6 sm:py-4 z-50 flex flex-col md:flex-row items-center justify-between gap-3 will-change-transform ${glassClass}`}>
          <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="p-2 bg-red-500/10 text-red-500 rounded-xl"><Volume2 className="h-4 w-4" /></div>
            <div className="text-right min-w-0"><p className="text-[10px] font-bold uppercase tracking-wider text-gray-500">در حال پخش ضبط مکالمه</p><p className={`text-xs sm:text-sm font-black mt-0.5 truncate max-w-[180px] ${textPrimary}`}>{currentAudio.name}</p></div>
          </div>
          <div className="w-full max-w-2xl flex-1"><audio src={currentAudio.url} controls autoPlay className="w-full h-8 accent-red-500 rounded-lg" /></div>
          <button onClick={() => setCurrentAudio(null)} className={`p-1.5 rounded-xl border w-full md:w-auto flex items-center justify-center gap-1.5 font-bold text-xs cursor-pointer ${isDarkMode ? 'bg-gray-800 border-gray-700 text-gray-400' : 'bg-white border-gray-300 text-gray-600'}`}><X className="h-3.5 w-3.5" /> بستن پنل</button>
        </div>
      )}

      {/* مدال گزارش مکالمه Wrap-Up */}
      {wrapupData && (
        <div className="fixed inset-0 h-screen w-screen bg-gray-950/80 backdrop-blur-md flex items-center justify-center p-3 z-50 pointer-events-auto">
          <div className={`w-full max-w-lg p-5 sm:p-8 rounded-2xl relative overflow-hidden max-h-[95vh] overflow-y-auto custom-scrollbar will-change-transform ${glassClass}`}>
            <div className="absolute top-0 right-0 w-full h-1.5 bg-gradient-to-l from-red-500 to-amber-500"></div>
            <div className="flex items-start gap-3 mb-5 border-b border-gray-700/20 pb-4">
              <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-xl border border-amber-500/20"><ClipboardCheck className="h-5 w-5" /></div>
              <div><h3 className={`text-lg sm:text-xl font-black ${textPrimary}`}>ثبت اجباری خلاصه مکالمه</h3><p className={`text-[11px] sm:text-xs mt-0.5 ${textSecondary}`}>میز کار قفل شد. ثبت سوابق تجاری فعال است.</p></div>
            </div>
            <div className={`p-3 rounded-xl space-y-2 mb-5 ${innerGlassClass}`}>
              <div className="flex justify-between items-center text-[10px]"><span className={textMuted}>مخاطب تماس</span><span className={textMuted}>خط ارتباطی</span></div>
              <div className="flex justify-between items-center gap-4"><p className={`font-black text-sm truncate ${textPrimary}`}>{wrapupData.caller_name}</p><p className="font-mono font-bold text-amber-400 text-left text-sm">{wrapupData.phone_number}</p></div>
            </div>
            <form onSubmit={handleWrapupFormSubmit} className="space-y-4">
              <div>
                <label className={`block text-xs font-bold uppercase tracking-wide mb-2 ${textSecondary}`}>نتیجه نهایی کسب و کار <span className="text-red-500">*</span></label>
                <select required value={wrapupForm.disposition} onChange={e => setWrapupForm({ ...wrapupForm, disposition: e.target.value })} className={`w-full border border-gray-700/60 rounded-lg p-3 text-sm focus:outline-none ${inputBg} ${textPrimary}`}>
                  <option value="" disabled hidden>-- انتخاب نتیجه تماس --</option>
                  <option value="SALE_CLOSED">🟢 فروش نهایی / قرارداد بسته شد</option>
                  <option value="INTERESTED">🔵 مشتری علاقه‌مند / برنامه‌ریزی پیگیری</option>
                  <option value="CALLBACK_REQUESTED">🟡 درخواست تماس مجدد / خط مشغول</option>
                  <option value="REJECTED">🔴 عدم تمایل / قطع ارتباط فرآیند</option>
                  <option value="SUPPORT_RESOLVED">🟣 تیکت پشتیبانی مشتری حل شد</option>
                </select>
              </div>
              <div>
                <label className={`block text-xs font-bold uppercase mb-2 ${textSecondary}`}>یادداشت جزئیات تماس</label>
                <div className="relative"><FileText className="absolute right-3 top-3.5 h-4 w-4 text-gray-500" /><textarea required value={wrapupForm.notes} onChange={e => setWrapupForm({ ...wrapupForm, notes: e.target.value })} rows="3" className={`w-full border border-gray-700/60 rounded-lg p-3 pr-10 text-sm focus:outline-none ${inputBg} ${textPrimary}`} placeholder="خلاصه جزئیات درخواست کارب..." /></div>
              </div>
              {wrapupError && (<div className="bg-red-950/40 border border-red-900 text-red-400 text-xs p-3 rounded-lg flex items-center gap-2"><AlertTriangle className="h-4 w-4" /> {wrapupError}</div>)}
              <button type="submit" disabled={isSubmittingWrapup || !wrapupForm.disposition} className="w-full bg-amber-500 hover:bg-amber-600 disabled:opacity-40 text-gray-950 font-black text-sm p-3 rounded-lg flex items-center justify-center gap-2 transition cursor-pointer"><CheckCircle className="h-4 w-4" />ثبت اطلاعات و باز کردن میز کار</button>
            </form>
          </div>
        </div>
      )}

    </div>
  </>
  );
}