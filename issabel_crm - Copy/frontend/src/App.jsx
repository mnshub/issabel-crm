import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import JsSIP from 'jssip';
import { Phone, User, Activity, LogOut, CheckCircle, XCircle, X, Save, FileText, Mail, ShieldCheck, PhoneCall, Loader2, Play, Volume2, Search, PhoneForwarded, BarChart3, TrendingUp, PhoneMissed, Lock, ShieldAlert, ClipboardCheck, AlertTriangle, Sun, Moon, PhoneOff } from 'lucide-react';

// تنظیم هدرهای پیش‌فرض اکسپورت فرکانس‌های میان‌سایتی به بک‌اند جنگو
axios.defaults.baseURL = 'http://127.0.0.1:8000';
axios.defaults.withCredentials = true; // اجبار پاس‌دادن کوکی‌های امنیتی سشن

export default function App() {
  const [authLoading, setAuthLoading] = useState(true); 
  const [isAuthenticated, setIsAuthenticated] = useState(false); 
  const [loading, setLoading] = useState(true);
  const [agentData, setAgentData] = useState(null);
  const [activeCall, setActiveCall] = useState(null);

  // حالت‌های مدیریت تم ظاهری سیستم (تاریک / روشن)
  const [isDarkMode, setIsDarkMode] = useState(true);

  // تغییرات فاز ۴: حالت‌های اختصاصی تلفن نرم‌افزاری تحت وب مرورگر (WebRTC Softphone)
  const [sipRegistered, setSipRegistered] = useState(false);
  const [sipCallState, setSipCallState] = useState('IDLE'); // IDLE, RINGING, CONNECTED
  const [activeSipSession, setActiveSipSession] = useState(null);
  const [sipError, setSipError] = useState('');
  
  // رفرنس‌های پایدار جهت حفظ سوکت و سشن در رندرهای متوالی کامپوننت
  const uaRef = useRef(null);
  const currentSessionRef = useRef(null);

  // فرم ورود کارشناسان
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // فرم اجباری خلاصه مکالمات (Post-Call Compliance Wrap-Up)
  const [wrapupData, setWrapupData] = useState(null); 
  const [wrapupForm, setWrapupForm] = useState({ disposition: '', notes: '' });
  const [isSubmittingWrapup, setIsSubmittingWrapup] = useState(false);
  const [wrapupError, setWrapupError] = useState('');

  // حالت‌های کشوی اطلاعات مشتری (Sliding Drawer)
  const [selectedPhone, setSelectedPhone] = useState(null);
  const [isAgentProfile, setIsAgentProfile] = useState(false); 
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [customerForm, setCustomerForm] = useState({ first_name: '', last_name: '', email: '', notes: '' });
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null); 

  // حالت‌های عملیاتی لایه مخابراتی
  const [dialingPhone, setDialingPhone] = useState(null);
  const [manualNumber, setManualNumber] = useState(''); 

  // پخش فایل‌های صوتی ضبط مکالمات
  const [currentAudio, setCurrentAudio] = useState(null); 

  // فیلتر جستجوی سوابق
  const [searchQuery, setSearchQuery] = useState(''); 

  // کلاس‌های استایل‌دهی شیشه‌ای (Glassmorphism UI Framework)
  const glassClass = isDarkMode 
    ? "bg-gray-900/60 backdrop-blur-lg border border-white/10 shadow-2xl" 
    : "bg-white/60 backdrop-blur-lg border border-gray-200/80 shadow-xl";

  const innerGlassClass = isDarkMode
    ? "bg-gray-950/50 border border-white/5"
    : "bg-gray-50/70 border border-gray-200/60";

  const textPrimary = isDarkMode ? "text-white" : "text-gray-900";
  const textSecondary = isDarkMode ? "text-gray-400" : "text-gray-600";
  const textMuted = isDarkMode ? "text-gray-500" : "text-gray-400";
  const inputBg = isDarkMode ? "bg-gray-950/80 focus:border-red-500" : "bg-white/90 focus:border-red-600 shadow-inner";

  // هوک بررسی اولیه احراز هویت کاربر هنگام بارگذاری صفحه
  useEffect(() => {
    axios.get('/api/auth/status/')
      .then(res => {
        if (res.data.authenticated) {
          setIsAuthenticated(true);
          fetchDashboardData();
        }
        setAuthLoading(false);
      })
      .catch(() => {
        setIsAuthenticated(false);
        setAuthLoading(false);
      });
  }, []);

  // واکشی آمارهای اصلی داشبورد و اطلاعات داخلی اختصاصی کارشناس
  const fetchDashboardData = () => {
    setLoading(true);
    axios.get('/api/dashboard/data/')
      .then(res => {
        setAgentData(res.data);
        setLoading(false);
        
        // همگام‌سازی داینامیک WebRTC با استفاده از اطلاعات و رمز عبور مستقیم پایگاه داده
        if (res.data.extension_number && res.data.extension_number !== "Not Assigned" && res.data.extension_secret) {
          initializeWebRTC(res.data.extension_number, res.data.extension_secret);
        }
      })
      .catch(err => {
        console.error("API error or missing session credentials:", err);
        setLoading(false);
      });
  };

  // موتور اصلی هندشیک و ریجستر وب‌ساکت تلفن داخلی به سرور ایزابل (Port 8089)
  const initializeWebRTC = (extension, secret) => {
    if (uaRef.current) return; // جلوگیری از باز کردن تردها و سوکت‌های تکراری روی شبکه مرورگر

    console.log(`🔌 Initializing WebRTC PJSIP Engine for Line Extension: ${extension}`);
    JsSIP.debug.enable('jssip:*'); // فعال‌سازی پورت ابزار تلمتری مانیتورینگ پروتکل در کنسول مرورگر

    const socket = new JsSIP.WebSocketInterface('wss://192.168.100.115:8089/ws'); 
    const config = {
      sockets: [socket],
      uri: `sip:${extension}@192.168.100.115`,
      password: secret, // دریافت داینامیک کلید سکرت اختصاصی افزوده شده به مدل جنگو
      register: true,
      session_timers: false
    };

    const ua = new JsSIP.UA(config);
    uaRef.current = ua;

    // مانیتورینگ چرخه ثبت داخلی روی مرکز تلفن ایزابل
    ua.on('registered', () => {
      console.log("🟢 WebRTC Extension Registered Successfully onto Issabel Core!");
      setSipRegistered(true);
      setSipError('');
    });

    ua.on('registrationFailed', (e) => {
      console.error("❌ WebRTC SIP Registration Refused:", e.cause);
      setSipRegistered(false);
      setSipError(`خطا در اتصال تلفن داخلی: ${e.cause}`);
    });

    // مدیریت لاین‌ها و استریم‌های صوتی ورودی (Inbound Session Handlers)
    ua.on('newRTCSession', (data) => {
      const session = data.session;
      currentSessionRef.current = session;
      setActiveSipSession(session);

      if (session.direction === 'incoming') {
        console.log("📥 Incoming WebRTC Call Channel Triggered!");
        setSipCallState('RINGING');
        setActiveCall({
          caller: session.remote_identity.display_name || session.remote_identity.uri.user,
          number: session.remote_identity.uri.user
        });
      }

      // تغییر وضعیت کامپوننت پس از پذیرش و اتصال کانال صوتی دوطرفه
      session.on('accepted', () => {
        console.log("📞 Call Connection Answered - Handshake Complete.");
        setSipCallState('CONNECTED');
        setActiveCall(null); // پاکسازی پاپ‌آپ وضعیت زنگ زدن فرعی
      });

      session.on('ended', () => {
        console.log("🛑 WebRTC Session Terminated Normally.");
        handleCallCleanup();
      });

      session.on('failed', (e) => {
        console.warn("❌ WebRTC Connection Interrupted/Refused:", e.cause);
        handleCallCleanup();
      });

      // روتینگ مستقیم بایت‌های صوتی رمزگشایی شده WebRTC به خروجی هدست کارشناس
      session.connection.addEventListener('track', (e) => {
        console.log("🔊 WebRTC Media Track Detected. Binding Stream to Headset Array...");
        const remoteAudio = document.getElementById('webRtcRemoteAudio');
        if (remoteAudio && e.streams[0]) {
          remoteAudio.srcObject = e.streams[0];
        }
      });
    });

    ua.start();
  };

  const handleCallCleanup = () => {
    setSipCallState('IDLE');
    setActiveSipSession(null);
    currentSessionRef.current = null;
    setActiveCall(null);
  };

  // کنترلرهای محلی دکمه‌های پاسخگویی و قطع تماس مرورگر
  const handleNativeSipAnswer = () => {
    if (currentSessionRef.current && sipCallState === 'RINGING') {
      const options = {
        mediaConstraints: { audio: true, video: false } // استفاده خالص از کانال صوت بدون ویدیو
      };
      currentSessionRef.current.answer(options);
    }
  };

  const handleNativeSipDecline = () => {
    if (currentSessionRef.current) {
      currentSessionRef.current.terminate();
      handleCallCleanup();
    }
  };

  // چرخه سوکت موازی با دافنه جنگو جهت مانیتورینگ ایونت‌های توزیع صف و خلاصه تماس‌ها
  useEffect(() => {
    if (!isAuthenticated) return; 

    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const socketUrl = `${protocol}127.0.0.1:8000/ws/calls/`;
    const socket = new WebSocket(socketUrl);

    socket.onopen = () => console.log("🚀 React App connected to Daphne WebSocket Engine!");
    
    socket.onmessage = (e) => {
      const data = JSON.parse(e.data);
      console.log("⚓ Intercepted Event Frame:", data);

      if (data.type === 'call_ringing') {
        if (sipCallState === 'IDLE') {
          setActiveCall({ caller: data.caller, number: data.number });
        }
      } else if (data.type === 'clear_notification') {
        if (sipCallState === 'IDLE') setActiveCall(null);
      } else if (data.type === 'show_wrapup') {
        setActiveCall(null); 
        setWrapupForm({ disposition: '', notes: '' }); 
        setWrapupError('');
        setWrapupData({
          phone_number: data.phone_number,
          caller_name: data.caller_name || 'مشتری خارجی'
        });
      }
    };

    return () => {
      socket.close();
      if (uaRef.current) {
        uaRef.current.stop();
        uaRef.current = null;
      }
    };
  }, [isAuthenticated, sipCallState]);

  // واکشی پروفایل مشتری هنگام باز شدن کشوی اطلاعات جانبی
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
        notes: 'این داخلی به عنوان یک دارایی در دفترچه تلفن مرکزی سازمان ثبت شده است. تنظیمات مربوطه از پنل مدیریتی اصلی قابل تغییر بوده و در این بخش امکان ویرایش آن وجود ندارد.'
      });
      setDrawerLoading(false);
      return;
    }

    axios.get(`/call/customer/lookup/${selectedPhone}/`)
      .then(res => {
        setCustomerForm({
          first_name: res.data.first_name || '',
          last_name: res.data.last_name || '',
          email: res.data.email || '',
          notes: res.data.notes || ''
        });
        setDrawerLoading(false);
      })
      .catch(err => {
        console.error("Failed to execute customer profile lookup:", err);
        setDrawerLoading(false);
      });
  }, [selectedPhone, isAgentProfile]);

  // فرآیند سابمیت فرم ورود کارشناس
  const handleLoginSubmit = (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setAuthError('');

    axios.post('/api/auth/login/', { username, password })
      .then(() => {
        setIsAuthenticated(true);
        fetchDashboardData(); 
        setIsSubmitting(false);
      })
      .catch(err => {
        setAuthError(err.response?.data?.message || 'نام کاربری یا رمز عبور اشتباه است.');
        setIsSubmitting(false);
      });
  };

  // ثبت فرآیند گزارش خلاصه تماس و باز کردن قفل کارتابل
  const handleWrapupFormSubmit = (e) => {
    e.preventDefault();
    if (!wrapupForm.disposition) {
      setWrapupError('جهت باز شدن میز کار، انتخاب نتیجه نهایی تماس الزامی است.');
      return;
    }
    
    setIsSubmittingWrapup(true);
    setWrapupError('');

    const payload = {
      phone_number: wrapupData.phone_number,
      disposition: wrapupForm.disposition,
      notes: wrapupForm.notes
    };

    axios.post('/api/call/wrapup/save/', payload)
      .then(() => {
        setWrapupData(null); 
        setIsSubmittingWrapup(false);
        fetchDashboardData(); 
      })
      .catch(err => {
        setWrapupError(err.response?.data?.message || 'خطا در ثبت و بروزرسانی اطلاعات.');
        setIsSubmittingWrapup(false);
      });
  };

  // عملیات خروج امن کارشناس و امحای نشست تلفنی وب‌ساکت مروگر
  const handleLogoutAction = () => {
    axios.get('/api/auth/logout/')
      .then(() => {
        setIsAuthenticated(false);
        setAgentData(null);
        setCurrentAudio(null);
        setSelectedPhone(null);
        if (uaRef.current) {
          uaRef.current.stop();
          uaRef.current = null;
        }
        setSipRegistered(false);
      })
      .catch(err => console.error("Error breaking session validation path:", err));
  };

  // لایه تماس‌های خروجی با سوییچ اتوماتیک بین WebRTC بومی یا روتینگ مستقیم AMI ایزابل
  const handleInitializeDial = (phoneNumber) => {
    if (!phoneNumber) return;
    const sanitizedNumber = phoneNumber.replace(/\s+/g, '');
    setDialingPhone(sanitizedNumber);

    // تماس مستقیم از مروگر در صورت ثبت موفق خط داخلی WebRTC
    if (sipRegistered && uaRef.current) {
      console.log(`🚀 Native WebRTC Outbound Dial Triggered for Target: ${sanitizedNumber}`);
      const options = {
        mediaConstraints: { audio: true, video: false }
      };
      const session = uaRef.current.call(`sip:${sanitizedNumber}@192.168.100.115`, options);
      currentSessionRef.current = session;
      setActiveSipSession(session);
      setSipCallState('CONNECTED');
      setTimeout(() => setDialingPhone(null), 1000);
      return;
    }

    // روتینگ بک‌آپ از طریق درخواست به هسته مدیریت اصلی ایزابل (Asterisk AMI)
    axios.get(`/call/dial/${sanitizedNumber}/`)
      .then(() => {
        setTimeout(() => setDialingPhone(null), 2500); 
      })
      .catch(err => {
        console.error("Asterisk AMI line origination handshake failed:", err);
        setDialingPhone(null);
      });
  };

  const handleManualCallSubmit = (e) => {
    e.preventDefault();
    if (!manualNumber) return;
    handleInitializeDial(manualNumber);
    setManualNumber(''); 
  };

  // بارگذاری آدرس فایل صوتی استریم ضبط مکالمات
  const handleLoadAudio = (logId, displayName) => {
    const streamUrl = `http://127.0.0.1:8000/call/play/${logId}/`;
    setCurrentAudio({
      id: logId,
      name: displayName,
      url: streamUrl
    });
  };

  // ثبت و ذخیره کارت مشخصات جدید مشتری
  const handleSaveCustomer = (e) => {
    e.preventDefault();
    if (isAgentProfile) return; 

    setIsSaving(true);
    setSaveStatus(null);

    const payload = {
      phone_number: selectedPhone,
      first_name: customerForm.first_name,
      last_name: customerForm.last_name,
      email: customerForm.email,
      notes: customerForm.notes
    };

    axios.post('/call/customer/save/', payload)
      .then(() => {
        setIsSaving(false);
        setSaveStatus('success');
        fetchDashboardData(); 
        setTimeout(() => setSaveStatus(null), 3000);
      })
      .catch(err => {
        console.error("Failed to commit profile updates to CRM database:", err);
        setIsSaving(false);
        setSaveStatus('error');
      });
  };

  const triggerDrawerOpening = (phoneNum, isAgentCheck) => {
    setIsAgentProfile(isAgentCheck);
    setSelectedPhone(phoneNum);
  };

  // محاسبات کلاینت‌ساید شاخص‌های کلیدی عملکرد (KPIs) کارشناس صف
  const rawInbound = agentData?.inbound_calls || [];
  const rawOutbound = agentData?.outbound_calls || [];
  const combinedCalls = [...rawInbound, ...rawOutbound];
  
  const totalCallsCount = combinedCalls.length;
  const answeredCount = combinedCalls.filter(c => c.disposition === 'ANSWERED').length;
  const missedCount = totalCallsCount - answeredCount;
  const successRatio = totalCallsCount > 0 ? Math.round((answeredCount / totalCallsCount) * 100) : 0;

  // فیلترینگ کلاینت‌ساید آرایه‌ها بر اساس کوئری جستجو
  const filteredInbound = rawInbound.filter(call => 
    call.display_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    call.other_phone.includes(searchQuery)
  );

  const filteredOutbound = rawOutbound.filter(call => 
    call.display_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    call.other_phone.includes(searchQuery)
  );

  if (authLoading) {
    return (
      <div className={`flex h-screen w-screen items-center justify-center transition-colors duration-500 ${isDarkMode ? 'bg-gray-950 text-gray-100' : 'bg-slate-100 text-gray-800'}`} dir="rtl">
        <div className="text-center px-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-red-500 border-t-transparent mx-auto"></div>
          <p className={`mt-4 font-medium text-sm sm:text-base ${textSecondary}`}>در حال بررسی نشست‌های امنیتی...</p>
        </div>
      </div>
    );
  }

  // نمایش فرم ورود در صورت عدم اهراز هویت سشن کاربری
  if (!isAuthenticated) {
    return (
      <div className={`min-h-screen w-full flex items-center justify-center p-4 sm:p-6 transition-all duration-500 ${isDarkMode ? 'bg-gradient-to-br from-gray-950 via-slate-900 to-zinc-950' : 'bg-gradient-to-br from-slate-100 via-zinc-200 to-gray-300'}`} dir="rtl">
        <div className={`w-full max-w-md p-6 sm:p-8 rounded-2xl relative overflow-hidden transition-all duration-300 ${glassClass}`}>
          <div className="absolute top-0 right-0 w-full h-1.5 bg-gradient-to-l from-red-500 to-red-800"></div>
          
          <div className="text-center mb-6 sm:mb-8">
            <div className={`h-11 w-11 sm:h-12 sm:w-12 rounded-xl flex items-center justify-center mx-auto mb-4 border ${isDarkMode ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-red-100 text-red-600 border-red-200'}`}>
              <Lock className="h-5 sm:h-6 sm:w-6 w-5" />
            </div>
            <h2 className={`text-xl sm:text-2xl font-black tracking-tight ${textPrimary}`}>احراز هویت ورود به سیستم</h2>
            <p className={`text-xs sm:text-sm mt-1 ${textSecondary}`}>جهت دسترسی به شبکه تلفنی، اطلاعات کاربری خود را وارد کنید.</p>
          </div>

          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <div>
              <label className={`block text-xs font-bold uppercase tracking-wide mb-2 ${textSecondary}`}>نام کاربری</label>
              <input 
                type="text"
                required
                value={username}
                onChange={e => setUsername(e.target.value)}
                className={`w-full border border-gray-700/60 rounded-lg p-3 text-sm transition font-medium focus:outline-none ${inputBg} ${textPrimary}`}
                placeholder="مثال: mohammad"
              />
            </div>

            <div>
              <label className={`block text-xs font-bold uppercase tracking-wide mb-2 ${textSecondary}`}>رمز عبور امنیتی</label>
              <input 
                type="password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                className={`w-full border border-gray-700/60 rounded-lg p-3 text-sm transition font-mono text-left focus:outline-none ${inputBg} ${textPrimary}`}
                placeholder="••••••••••••"
              />
            </div>

            {authError && (
              <div className="bg-red-950/40 border border-red-900 text-red-400 text-xs p-3 rounded-lg flex items-center gap-2 font-medium animate-fadeIn">
                <ShieldAlert className="h-4 w-4 flex-shrink-0" /> {authError}
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-red-500 hover:bg-red-600 text-white font-bold text-sm p-3 rounded-lg flex items-center justify-center gap-2 shadow-lg transition active:scale-[0.99] disabled:opacity-50 mt-4 sm:mt-6"
            >
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'ورود به سیستم'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={`flex h-screen w-screen items-center justify-center transition-all duration-500 ${isDarkMode ? 'bg-gray-950 text-gray-100' : 'bg-slate-100 text-gray-800'}`} dir="rtl">
        <div className="text-center px-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-red-500 border-t-transparent mx-auto"></div>
          <p className={`mt-4 font-medium text-sm sm:text-base ${textSecondary}`}>در حال راه‌اندازی موتور تلفنی...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen p-3 sm:p-6 relative overflow-x-hidden pb-40 transition-all duration-500 ${isDarkMode ? 'bg-gradient-to-br from-gray-950 via-slate-900 to-zinc-950 text-gray-100' : 'bg-gradient-to-br from-slate-50 via-zinc-100 to-gray-200 text-gray-800'}`} dir="rtl">
      
      {/* تگ پنهان صوتی HTML5 جهت لود استریم دکریپت شده صدا مستقیم از وب‌آرتی‌سی */}
      <audio id="webRtcRemoteAudio" autoPlay className="hidden" />

      {/* کانتینر بدنه اصلی با افکت تار شدن هنگام قفل فرآیند خلاصه مکالمه */}
      <div className={`transition-all duration-500 ease-in-out ${selectedPhone ? 'xl:pl-96' : ''} ${wrapupData ? 'blur-sm pointer-events-none' : ''}`}>
        
        {/* هدر بالایی داشبورد شیشه‌ای */}
        <header className="flex flex-col md:flex-row gap-4 justify-between items-center p-4 rounded-xl mb-6 transition-all duration-300 class glass-card border border-white/10 shadow-2xl relative">
          <div className="flex items-center gap-3">
            <div className={`h-3 w-3 rounded-full animate-pulse ${sipRegistered ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <h1 className={`text-lg sm:text-xl font-black tracking-tight ${textPrimary}`}>
              داشبورد سی‌آر‌ام <span className="text-red-500">ایزابل</span>
              {sipRegistered && <span className="text-[10px] mr-2 bg-green-500/10 border border-green-500/20 text-green-400 font-mono px-2 py-0.5 rounded-md font-bold">WebRTC فعال</span>}
            </h1>
          </div>
          <div className="flex flex-wrap items-center justify-center md:justify-end gap-3 text-xs sm:text-sm font-semibold w-full md:w-auto">
            {sipError && <div className="text-xs text-red-400 font-bold ml-2 animate-pulse">{sipError}</div>}
            <button
              onClick={() => setIsDarkMode(!isDarkMode)}
              className={`p-2 rounded-md border transition-all duration-300 flex items-center justify-center shadow-sm cursor-pointer ${isDarkMode ? 'bg-gray-800 text-yellow-400 border-gray-700 hover:bg-gray-700' : 'bg-white text-indigo-600 border-gray-300 hover:bg-gray-100'}`}
            >
              {isDarkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <span className={`px-3 py-1.5 rounded-md border transition-all duration-300 ${innerGlassClass} ${textSecondary}`}>
              کارشناس: <strong className={textPrimary}>{agentData?.agent_name || 'مهمان'}</strong>
            </span>
            <span className={`px-3 py-1.5 rounded-md border transition-all duration-300 ${innerGlassClass} ${textSecondary}`}>
              داخلی: <strong className="text-red-500 font-mono">{agentData?.extension_number || '---'}</strong>
            </span>
            <button 
              onClick={handleLogoutAction}
              className={`p-1.5 sm:p-2 border rounded-md transition flex items-center gap-1.5 cursor-pointer shadow-sm text-xs sm:text-sm ${isDarkMode ? 'bg-gray-800 hover:bg-red-950 hover:text-red-400 text-gray-400 border-gray-700' : 'bg-white hover:bg-red-50 hover:text-red-600 text-gray-600 border-gray-300'}`}
            >
              <LogOut className="h-3.5 w-3.5 sm:h-4 sm:w-4 transform rotate-180" />
              <span>خروج</span>
            </button>
          </div>
        </header>

        {/* بخش کارت‌های آمار پیشرفته کارایی کارشناس */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className={`p-4 rounded-xl shadow-md flex items-center justify-between transition-all duration-300 ${glassClass}`}>
            <div>
              <p className={`text-xs font-bold uppercase tracking-wider ${textSecondary}`}>کل تماس‌ها</p>
              <h3 className={`text-2xl font-black mt-1 font-mono ${textPrimary}`}>{totalCallsCount}</h3>
            </div>
            <div className={`p-3 rounded-lg ${isDarkMode ? 'bg-gray-800 text-gray-400' : 'bg-slate-200 text-gray-600'}`}><BarChart3 className="h-5 w-5" /></div>
          </div>
          <div className={`p-4 rounded-xl shadow-md flex items-center justify-between transition-all duration-300 ${glassClass}`}>
            <div>
              <p className={`text-xs font-bold uppercase tracking-wider ${textSecondary}`}>پاسخ داده شده</p>
              <h3 className="text-2xl font-black text-green-500 mt-1 font-mono">{answeredCount}</h3>
            </div>
            <div className="p-3 bg-green-500/10 text-green-500 rounded-lg"><TrendingUp className="h-5 w-5" /></div>
          </div>
          <div className={`p-4 rounded-xl shadow-md flex items-center justify-between transition-all duration-300 ${glassClass}`}>
            <div>
              <p className={`text-xs font-bold uppercase tracking-wider ${textSecondary}`}>از دست رفته</p>
              <h3 className="text-2xl font-black text-red-500 mt-1 font-mono">{missedCount}</h3>
            </div>
            <div className="p-3 bg-red-500/10 text-red-500 rounded-lg"><PhoneMissed className="h-5 w-5" /></div>
          </div>
          <div className={`p-4 rounded-xl shadow-md flex items-center justify-between transition-all duration-300 ${glassClass}`}>
            <div>
              <p className={`text-xs font-bold uppercase tracking-wider ${textSecondary}`}>نرخ موفقیت</p>
              <h3 className="text-2xl font-black text-blue-500 mt-1 font-mono">{successRatio}%</h3>
            </div>
            <div className="p-3 bg-blue-500/10 text-blue-500 rounded-lg"><Activity className="h-5 w-5" /></div>
          </div>
        </section>

        {/* پنل شماره‌گیری سریع دستی و نوار فیلتر سرچ */}
        <section className={`p-4 rounded-xl mb-6 shadow-md flex flex-col md:flex-row gap-4 items-center justify-between transition-all duration-300 ${glassClass}`}>
          <div className="relative w-full md:max-w-md">
            <Search className="absolute right-3.5 top-3.5 h-4 w-4 text-gray-500" />
            <input 
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="جستجوی سوابق بر اساس نام یا شماره..."
              className={`w-full border border-gray-700/60 rounded-lg pr-10 pl-4 py-2.5 text-sm transition focus:outline-none ${inputBg} ${textPrimary}`}
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className={`absolute left-3 top-3.5 hover:${textPrimary} ${textMuted}`}><X className="h-4 w-4" /></button>
            )}
          </div>

          <form onSubmit={handleManualCallSubmit} className="flex gap-2 w-full md:w-auto items-center justify-between">
            <div className="relative w-full md:w-56">
              <input 
                type="text"
                required
                value={manualNumber}
                onChange={e => setManualNumber(e.target.value.replace(/[^0-9]/g, ''))} 
                placeholder="شماره‌گیری جدید..."
                className={`w-full border border-gray-700/60 rounded-lg px-3 py-2.5 text-sm font-mono transition text-left focus:outline-none ${inputBg} ${textPrimary}`}
              />
            </div>
            <button
              type="submit"
              disabled={dialingPhone !== null || !manualNumber}
              className="px-4 py-2.5 bg-green-600 hover:bg-green-700 disabled:opacity-40 text-white font-bold text-sm rounded-lg flex items-center gap-2 transition whitespace-nowrap cursor-pointer shadow-md"
            >
              {dialingPhone === manualNumber ? <Loader2 className="h-4 w-4 animate-spin" /> : <PhoneForwarded className="h-4 w-4 transform rotate-180" />}
              تماس
            </button>
          </form>
        </section>

        {/* گرید پنل‌های مانیتورینگ دو ستونه تماس‌ها */}
        <main className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          
          {/* ستون لاین تماس‌های ورودی */}
          <div className={`p-4 sm:p-5 rounded-xl shadow-lg transition-all duration-300 ${glassClass}`}>
            <h2 className={`text-base sm:text-lg font-black flex items-center justify-between mb-4 border-b pb-3 ${isDarkMode ? 'border-white/10 text-white' : 'border-gray-200 text-gray-900'}`}>
              <span className="flex items-center gap-2"><span className="text-green-400">📥</span> تماس‌های ورودی</span>
              <span className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${isDarkMode ? 'bg-gray-800 text-gray-400' : 'bg-slate-200 text-gray-600'}`}>{filteredInbound.length} مورد</span>
            </h2>
            <div className="space-y-2 max-h-[500px] overflow-y-auto pl-1 select-none custom-scrollbar">
              {filteredInbound.map(call => (
                <div 
                  key={call.id} 
                  onClick={() => triggerDrawerOpening(call.other_phone, call.is_agent)}
                  className={`flex flex-col sm:flex-row justify-between items-start sm:items-center p-3 rounded-lg border cursor-pointer gap-3 transition-all duration-300 ${isDarkMode ? 'bg-gray-950/40 border-white/5 hover:border-gray-700' : 'bg-white/80 border-gray-200 hover:border-gray-400'} ${selectedPhone === call.other_phone ? 'border-red-500 bg-red-500/5' : ''}`}
                >
                  <div className="flex items-center gap-3 w-full sm:w-auto">
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleInitializeDial(call.other_phone); }}
                      disabled={dialingPhone !== null}
                      className={`p-2 rounded-lg border flex-shrink-0 transition-colors ${dialingPhone === call.other_phone ? 'bg-yellow-950 text-yellow-400 border-yellow-800' : 'bg-green-500/10 text-green-500 border-green-500/30 hover:bg-green-500 hover:text-white'}`}
                    >
                      {dialingPhone === call.other_phone ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <PhoneCall className="h-3.5 w-3.5" />}
                    </button>
                    <div className="truncate">
                      <div className="flex items-center gap-2">
                        <p className={`font-bold truncate text-sm sm:text-base ${textPrimary}`}>{call.display_name}</p>
                        {call.is_agent && (
                          <span className="text-[9px] bg-blue-500/10 text-blue-500 border border-blue-500/30 px-1.5 py-0.5 rounded font-bold tracking-wider flex-shrink-0">تیم</span>
                        )}
                      </div>
                      <p className={`text-xs mt-0.5 ${textSecondary}`}>شماره: <span className="font-mono">{call.other_phone}</span> • <span className="font-mono">{call.call_time}</span></p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between sm:justify-end gap-3 w-full sm:w-auto border-t sm:border-t-0 border-gray-800/20 pt-2 sm:pt-0">
                    {call.duration !== '---' && <span className={`text-xs font-mono ${textSecondary}`}>{call.duration}</span>}
                    {call.disposition === 'ANSWERED' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleLoadAudio(call.id, call.display_name); }}
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
              {filteredInbound.length === 0 && (
                <p className={`text-sm text-center py-12 ${textMuted}`}>هیچ رکورد ورودی یافت نشد.</p>
              )}
            </div>
          </div>

          {/* ستون لاین تماس‌های خروجی */}
          <div className={`p-4 sm:p-5 rounded-xl shadow-lg transition-all duration-300 ${glassClass}`}>
            <h2 className={`text-base sm:text-lg font-black flex items-center justify-between mb-4 border-b pb-3 ${isDarkMode ? 'border-white/10 text-white' : 'border-gray-200 text-gray-900'}`}>
              <span className="flex items-center gap-2"><span className="text-blue-500">📤</span> تماس‌های خروجی</span>
              <span className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${isDarkMode ? 'bg-gray-800 text-gray-400' : 'bg-slate-200 text-gray-600'}`}>{filteredOutbound.length} مورد</span>
            </h2>
            <div className="space-y-2 max-h-[500px] overflow-y-auto pl-1 select-none custom-scrollbar">
              {filteredOutbound.map(call => (
                <div 
                  key={call.id} 
                  onClick={() => triggerDrawerOpening(call.other_phone, call.is_agent)}
                  className={`flex flex-col sm:flex-row justify-between items-start sm:items-center p-3 rounded-lg border cursor-pointer gap-3 transition-all duration-300 ${isDarkMode ? 'bg-gray-950/40 border-white/5 hover:border-gray-700' : 'bg-white/80 border-gray-200 hover:border-gray-400'} ${selectedPhone === call.other_phone ? 'border-red-500 bg-red-500/5' : ''}`}
                >
                  <div className="flex items-center gap-3 w-full sm:w-auto">
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleInitializeDial(call.other_phone); }}
                      disabled={dialingPhone !== null}
                      className={`p-2 rounded-lg border flex-shrink-0 transition-colors ${dialingPhone === call.other_phone ? 'bg-yellow-950 text-yellow-400 border-yellow-800' : 'bg-green-500/10 text-green-500 border-green-500/30 hover:bg-green-500 hover:text-white'}`}
                    >
                      {dialingPhone === call.other_phone ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <PhoneCall className="h-3.5 w-3.5" />}
                    </button>
                    <div className="truncate">
                      <div className="flex items-center gap-2">
                        <p className={`font-bold truncate text-sm sm:text-base ${textPrimary}`}>{call.display_name}</p>
                        {call.is_agent && (
                          <span className="text-[9px] bg-blue-500/10 text-blue-500 border border-blue-500/30 px-1.5 py-0.5 rounded font-bold tracking-wider flex-shrink-0">تیم</span>
                        )}
                      </div>
                      <p className={`text-xs mt-0.5 ${textSecondary}`}>شماره: <span className="font-mono">{call.other_phone}</span> • <span className="font-mono">{call.call_time}</span></p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between sm:justify-end gap-3 w-full sm:w-auto border-t sm:border-t-0 border-gray-800/20 pt-2 sm:pt-0">
                    {call.duration !== '---' && <span className={`text-xs font-mono ${textSecondary}`}>{call.duration}</span>}
                    {call.disposition === 'ANSWERED' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleLoadAudio(call.id, call.display_name); }}
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
              {filteredOutbound.length === 0 && (
                <p className={`text-sm text-center py-12 ${textMuted}`}>هیچ رکورد خروجی یافت نشد.</p>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* کشوی متحرک پروفایل مشتری تعاملی سی‌آر‌ام */}
      <div className={`fixed top-0 left-0 h-full w-full max-w-md sm:w-96 border-r shadow-2xl p-6 transition-transform duration-500 ease-in-out z-40 ${glassClass} ${selectedPhone ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex flex-col h-full">
          
          <div className={`flex justify-between items-center border-b pb-4 mb-6 ${isDarkMode ? 'border-white/10' : 'border-gray-200'}`}>
            <div className="flex items-center gap-2">
              <User className="h-5 w-5 text-red-500" />
              <h3 className={`text-lg font-black ${textPrimary}`}>
                {isAgentProfile ? 'نود داخلی سیستم' : 'میز کار مشتری'}
              </h3>
            </div>
            <button 
              onClick={() => setSelectedPhone(null)}
              className={`p-1.5 rounded-lg border cursor-pointer transition ${isDarkMode ? 'bg-gray-800 border-gray-700 text-gray-400 hover:text-white' : 'bg-white border-gray-300 text-gray-500 hover:text-gray-900'}`}
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {drawerLoading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-red-500 border-t-transparent"></div>
            </div>
          ) : (
            <form onSubmit={handleSaveCustomer} className="flex-1 flex flex-col justify-between overflow-y-auto pr-1 custom-scrollbar">
              <div className="space-y-4">
                
                <div className={`border p-3 rounded-lg flex items-center justify-between gap-3 mb-2 ${isAgentProfile ? 'bg-blue-500/10 border-blue-500/20' : 'bg-gray-950/20 border-gray-800/40'}`}>
                  <div className="flex items-center gap-3">
                    <Phone className={`h-4 w-4 ${isAgentProfile ? 'text-blue-500' : 'text-green-500'}`} />
                    <div>
                      <p className={`text-xs font-bold uppercase tracking-wider ${textMuted}`}>شماره ارتباطی</p>
                      <p className={`text-sm font-mono font-bold text-left ${textPrimary}`}>{selectedPhone}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    disabled={dialingPhone !== null}
                    onClick={() => handleInitializeDial(selectedPhone)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold border transition ${dialingPhone === selectedPhone ? 'bg-yellow-950 text-yellow-400 border-yellow-800' : 'bg-green-500/10 text-green-500 border-green-500/30 hover:bg-green-500 hover:text-white'}`}
                  >
                    {dialingPhone === selectedPhone ? <Loader2 className="h-3 w-3 animate-spin" /> : <PhoneCall className="h-3 w-3" />}
                    {dialingPhone === selectedPhone ? 'شماره‌گیری...' : 'تماس'}
                  </button>
                </div>

                {isAgentProfile ? (
                  <div className={`space-y-4 p-4 rounded-xl shadow-inner border ${innerGlassClass}`}>
                    <div className="flex items-center gap-2 text-blue-500 font-bold text-sm border-b border-gray-800/20 pb-2">
                      <ShieldCheck className="h-4 w-4" /> اطلاعات پروفایل همکار سازمان
                    </div>
                    <div>
                      <span className={`text-[10px] uppercase font-black block tracking-wide ${textMuted}`}>پیش‌نمایش نام</span>
                      <span className={`text-base font-bold mt-1 block ${textPrimary}`}>{customerForm.first_name}</span>
                    </div>
                    <div>
                      <span className={`text-[10px] uppercase font-black block tracking-wide ${textMuted}`}>بستر زیرساخت</span>
                      <span className={`text-sm font-medium mt-1 block ${textSecondary}`}>{customerForm.email}</span>
                    </div>
                    <div className="pt-2 border-t border-gray-800/10">
                      <p className={`text-xs leading-relaxed italic p-2.5 rounded-lg border ${innerGlassClass} ${textSecondary}`}>{customerForm.notes}</p>
                    </div>
                  </div>
                ) : (
                  <>
                    <div>
                      <label className={`block text-xs font-bold uppercase tracking-wide mb-2 ${textSecondary}`}>نام</label>
                      <input 
                        type="text" 
                        required
                        value={customerForm.first_name}
                        onChange={e => setCustomerForm({ ...customerForm, first_name: e.target.value })}
                        className={`w-full border border-gray-700/60 rounded-lg p-2.5 text-sm transition focus:outline-none ${inputBg} ${textPrimary}`}
                        placeholder="محمد"
                      />
                    </div>

                    <div>
                      <label className={`block text-xs font-bold uppercase tracking-wide mb-2 ${textSecondary}`}>نام خانوادگی</label>
                      <input 
                        type="text" 
                        value={customerForm.last_name}
                        onChange={e => setCustomerForm({ ...customerForm, last_name: e.target.value })}
                        className={`w-full border border-gray-700/60 rounded-lg p-2.5 text-sm transition focus:outline-none ${inputBg} ${textPrimary}`}
                        placeholder="منصوری"
                      />
                    </div>

                    <div>
                      <label className={`block text-xs font-bold uppercase tracking-wide mb-2 ${textSecondary}`}>آدرس ایمیل</label>
                      <div className="relative">
                        <Mail className="absolute right-3 top-3.5 h-4 w-4 text-gray-500" />
                        <input 
                          type="email" 
                          value={customerForm.email}
                          onChange={e => setCustomerForm({ ...customerForm, email: e.target.value })}
                          className={`w-full border border-gray-700/60 rounded-lg p-2.5 pr-10 text-sm transition text-left font-mono focus:outline-none ${inputBg} ${textPrimary}`}
                          placeholder="name@company.com"
                        />
                      </div>
                    </div>

                    <div>
                      <label className={`block text-xs font-bold uppercase tracking-wide mb-2 ${textSecondary}`}>یادداشت‌های عملیاتی</label>
                      <div className="relative">
                        <FileText className="absolute right-3 top-3.5 h-4 w-4 text-gray-500" />
                        <textarea 
                          value={customerForm.notes}
                          onChange={e => setCustomerForm({ ...customerForm, notes: e.target.value })}
                          rows="4"
                          className={`w-full border border-gray-700/60 rounded-lg p-2.5 pr-10 text-sm transition resize-none focus:outline-none ${inputBg} ${textPrimary}`}
                          placeholder="جزئیات تعاملات و سوابق مشتری را وارد نمایید..."
                        ></textarea>
                      </div>
                    </div>
                  </>
                )}

                {saveStatus === 'success' && (
                  <div className="bg-green-500/10 border border-green-500/20 text-green-500 text-xs p-3 rounded-lg flex items-center gap-2 font-medium">
                    <CheckCircle className="h-4 w-4" /> اطلاعات مشتری با موفقیت همگام‌سازی شد!
                  </div>
                )}
                {saveStatus === 'error' && (
                  <div className="bg-red-500/10 border border-red-500/20 text-red-500 text-xs p-3 rounded-lg flex items-center gap-2 font-medium">
                    <XCircle className="h-4 w-4" /> خطا در ذخیره‌سازی اطلاعات.
                  </div>
                )}
              </div>

              {isAgentProfile ? (
                <div className="bg-blue-500/10 border border-blue-500/20 p-3 rounded-lg text-blue-500 text-center font-bold text-[11px] tracking-wide mt-6">
                  🔒 عدم دسترسی • شناسه داخلی قفل شده است
                </div>
              ) : (
                <button
                  type="submit"
                  disabled={isSaving}
                  className="w-full bg-red-500 hover:bg-red-600 text-white font-bold text-sm p-3 rounded-lg flex items-center justify-center gap-2 shadow-lg transition active:scale-[0.99] disabled:opacity-50 mt-6 cursor-pointer"
                >
                  <Save className="h-4 w-4" />
                  {isSaving ? 'در حال ذخیره‌سازی...' : 'ذخیره کارت مشتری'}
                </button>
              )}
            </form>
          )}
        </div>
      </div>

      {/* پاپ‌آپ هوشمند هشدار تماس ورودی با ماژول کلید کنترل زنده (WebRTC Call Controls) */}
      {activeCall && (
        <div className={`fixed bottom-4 left-4 right-4 sm:left-auto sm:right-6 sm:bottom-6 w-auto sm:w-80 border-r-8 rounded-xl p-4 sm:p-5 z-50 shadow-2xl transition-all duration-300 ${glassClass} ${sipCallState === 'RINGING' ? 'border-amber-500 animate-pulse' : 'border-green-500 animate-bounce'}`}>
          <div className="flex items-start gap-4">
            <div className={`p-2.5 sm:p-3 rounded-lg ${sipCallState === 'RINGING' ? 'bg-amber-500/10 text-amber-400' : 'bg-green-500/10 text-green-400'}`}>
              <Phone className="h-5 w-5 sm:h-6 sm:w-6" />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400">
                {sipCallState === 'RINGING' ? 'تماس ورودی زنده (WebRTC)...' : 'تماس ورودی جدید...'}
              </h4>
              <h3 className={`text-lg sm:text-xl font-black mt-1 truncate ${textPrimary}`}>{activeCall.caller}</h3>
              <p className={`text-xs sm:text-sm mt-0.5 ${textSecondary}`}>خط: <span className="font-mono">{activeCall.number}</span></p>
              
              {/* کلیدهای تعاملی پاسخ و رد مکالمه وب‌آرتی‌سی داخل مرورگر */}
              {sipCallState === 'RINGING' && (
                <div className="flex gap-2 mt-4">
                  <button
                    onClick={handleNativeSipAnswer}
                    className="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold text-xs py-2 px-3 rounded-md flex items-center justify-center gap-1 transition shadow-md cursor-pointer"
                  >
                    <PhoneCall className="h-3 w-3" /> پاسخ تماس
                  </button>
                  <button
                    onClick={handleNativeSipDecline}
                    className="flex-1 bg-red-600 hover:bg-red-700 text-white font-bold text-xs py-2 px-3 rounded-md flex items-center justify-center gap-1 transition shadow-md cursor-pointer"
                  >
                    <PhoneOff className="h-3 w-3" /> رد تماس
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* بنر شناور هشدار مکالمه زنده و فعال متصل شده در بالای داشبورد */}
      {sipCallState === 'CONNECTED' && activeSipSession && (
        <div className="fixed top-24 left-1/2 transform -translate-x-1/2 bg-green-500/10 border border-green-500/30 text-green-400 text-xs py-2 px-6 rounded-full font-black flex items-center gap-3 shadow-xl backdrop-blur-md z-40 animate-pulse">
          <Activity className="h-3.5 w-3.5 animate-spin" />
          <span>مکالمه زنده برقرار است • شماره: <strong className="font-mono">{activeSipSession.remote_identity.uri.user}</strong></span>
          <button 
            onClick={handleNativeSipDecline}
            className="bg-red-600 hover:bg-red-700 text-white font-bold rounded-full p-1 mr-2 transition-all cursor-pointer"
            title="قطع مکالمه"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      )}

      {/* فوتر داک شده پلیر صوتی پخش فایل صوتی ضبط مکالمات */}
      {currentAudio && (
        <div className={`fixed bottom-0 left-0 right-0 w-full border-t px-4 py-3 sm:px-6 sm:py-4 z-50 animate-slideUp flex flex-col md:flex-row items-center justify-between gap-3 ${glassClass}`}>
          <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="p-2 bg-red-500/10 text-red-500 rounded-xl animate-pulse">
              <Volume2 className="h-4 w-4 sm:h-5 sm:w-5" />
            </div>
            <div className="text-right min-w-0">
              <p className={`text-[10px] font-bold uppercase tracking-wider ${textMuted}`}>در حال پخش ضبط مکالمه</p>
              <p className={`text-xs sm:text-sm font-black mt-0.5 truncate max-w-[180px] sm:max-w-xs ${textPrimary}`}>{currentAudio.name}</p>
            </div>
          </div>
          
          <div className="w-full max-w-2xl flex-1">
            <audio 
              src={currentAudio.url} 
              controls 
              autoPlay 
              className="w-full h-8 sm:h-9 accent-red-500 rounded-lg"
            />
          </div>

          <button
            onClick={() => setCurrentAudio(null)}
            className={`p-1.5 sm:p-2 rounded-xl border transition w-full md:w-auto flex items-center justify-center gap-1.5 font-bold text-xs cursor-pointer ${isDarkMode ? 'bg-gray-800 border-gray-700 text-gray-400' : 'bg-white border-gray-300 text-gray-600'}`}
          >
            <X className="h-3.5 w-3.5" /> بستن پنل
          </button>
        </div>
      )}

      {/* مدال اجباری پس از تماس جهت ثبت سوابق تجاری و باز کردن قفل پنل */}
      {wrapupData && (
        <div className="fixed inset-0 h-screen w-screen bg-gray-950/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-4 z-50 pointer-events-auto">
          <div className={`w-full max-w-lg p-5 sm:p-8 rounded-2xl relative overflow-hidden animate-fadeIn max-h-[95vh] overflow-y-auto custom-scrollbar ${glassClass}`}>
            <div className="absolute top-0 right-0 w-full h-1.5 bg-gradient-to-l from-red-500 to-amber-500"></div>
            
            <div className="flex items-start gap-3 sm:gap-4 mb-5 border-b border-gray-700/20 pb-4">
              <div className="p-2.5 sm:p-3 bg-amber-500/10 text-amber-400 rounded-xl border border-amber-500/20 flex-shrink-0">
                <ClipboardCheck className="h-5 w-5 sm:h-6 sm:w-6 animate-pulse" />
              </div>
              <div>
                <h3 className={`text-lg sm:text-xl font-black tracking-tight ${textPrimary}`}>ثبت اجباری خلاصه مکالمه</h3>
                <p className={`text-[11px] sm:text-xs mt-0.5 ${textSecondary}`}>میز کار قفل شد. ثبت سوابق امنیتی و مدیریتی فعال است.</p>
              </div>
            </div>

            <div className={`p-3 sm:p-4 rounded-xl space-y-2 mb-5 ${innerGlassClass}`}>
              <div className="flex justify-between items-center text-[10px] sm:text-xs">
                <span className={textMuted}>مخاطب تماس</span>
                <span className={textMuted}>خط ارتباطی</span>
              </div>
              <div className="flex justify-between items-center gap-4">
                <p className={`font-black text-sm sm:text-base truncate ${textPrimary}`}>{wrapupData.caller_name}</p>
                <p className="font-mono font-bold text-amber-400 text-left text-sm sm:text-base">{wrapupData.phone_number}</p>
              </div>
            </div>

            <form onSubmit={handleWrapupFormSubmit} className="space-y-4">
              <div>
                <label className={`block text-xs font-bold uppercase tracking-wide mb-2 ${textSecondary}`}>
                  نتیجه نهایی کسب و کار <span className="text-red-500">*</span>
                </label>
                <select
                  required
                  value={wrapupForm.disposition}
                  onChange={e => setWrapupForm({ ...wrapupForm, disposition: e.target.value })}
                  className={`w-full border border-gray-700/60 rounded-lg p-3 text-sm transition font-medium cursor-pointer focus:outline-none ${inputBg} ${textPrimary}`}
                >
                  <option value="" disabled hidden>-- انتخاب نتیجه تماس --</option>
                  <option value="SALE_CLOSED">🟢 فروش نهایی / قرارداد بسته شد</option>
                  <option value="INTERESTED">🔵 مشتری علاقه‌مند / برنامه‌ریزی پیگیری</option>
                  <option value="CALLBACK_REQUESTED">🟡 درخواست تماس مجدد / خط مشغول</option>
                  <option value="REJECTED">🔴 عدم تمایل / قطع ارتباط فرآیند</option>
                  <option value="SUPPORT_RESOLVED">🟣 تیکت پشتیبانی مشتری حل شد</option>
                </select>
              </div>

              <div>
                <label className={`block text-xs font-bold uppercase tracking-wide mb-2 ${textSecondary}`}>یادداشت جزئیات تماس</label>
                <div className="relative">
                  <FileText className="absolute right-3 top-3.5 h-4 w-4 text-gray-500" />
                  <textarea
                    required
                    value={wrapupForm.notes}
                    onChange={e => setWrapupForm({ ...wrapupForm, notes: e.target.value })}
                    rows="3"
                    className={`w-full border border-gray-700/60 rounded-lg p-3 pr-10 text-sm transition resize-none placeholder-gray-600 focus:outline-none ${inputBg} ${textPrimary}`}
                    placeholder="خلاصه جزئیات درخواست کاربر، سوالات قیمت‌گذاری یا نتایج زمان‌بندی را بنویسید..."
                  />
                </div>
              </div>

              {wrapupError && (
                <div className="bg-red-950/40 border border-red-900 text-red-400 text-xs p-3 rounded-lg flex items-center gap-2 font-medium">
                  <AlertTriangle className="h-4 w-4 flex-shrink-0" /> {wrapupError}
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmittingWrapup || !wrapupForm.disposition}
                className="w-full bg-amber-500 hover:bg-amber-600 disabled:opacity-40 text-gray-950 font-black text-sm p-3 sm:p-3.5 rounded-lg flex items-center justify-center gap-2 shadow-xl transition active:scale-[0.99] mt-4 cursor-pointer"
              >
                {isSubmittingWrapup ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                {isSubmittingWrapup ? 'در حال همگام‌سازی نتایج...' : 'ثبت اطلاعات و باز کردن میز کار'}
              </button>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
