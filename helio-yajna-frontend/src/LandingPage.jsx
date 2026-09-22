import React from 'react'
import { motion } from 'framer-motion'
import { Zap, Globe, FileSpreadsheet, Sparkles, ArrowRight } from 'lucide-react'

const LandingPage = ({ onStart }) => {
    const features = [
        {
            icon: <Zap className="w-6 h-6 text-yellow-400" />,
            title: "Advanced Detection",
            description: "High-precision YOLOv12 models fine-tuned for satellite rooftop analysis."
        },
        {
            icon: <Globe className="w-6 h-6 text-blue-400" />,
            title: "Global Coverage",
            description: "Analyze locations worldwide with high-resolution satellite imagery feeds."
        },
        {
            icon: <FileSpreadsheet className="w-6 h-6 text-green-400" />,
            title: "Bulk Processing",
            description: "Upload CSV or Excel files to process hundreds of coordinates at once."
        }
    ];

    return (
        <div className="flex-1 flex flex-col items-center justify-center bg-[#0d0b09] p-6 md:p-12 overflow-y-auto custom-scrollbar text-[#EAE7DD]">
            {/* Hero Section */}
            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="text-center max-w-4xl mb-16"
            >
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#99775C]/15 border border-[#99775C]/30 mb-6">
                    <Sparkles className="w-3.5 h-3.5 text-[#99775C]" />
                    <span className="text-[10px] font-bold text-[#EAE7DD] uppercase tracking-[0.2em]">Helio Yajna Solar AI</span>
                </div>
                
                <h1 className="text-5xl md:text-7xl font-bold leading-tight tracking-tight mb-8 bg-gradient-to-b from-[#EAE7DD] via-[#EAE7DD]/90 to-[#99775C] bg-clip-text text-transparent font-serif">
                    Helio Yajna <br />Solar Intelligence.
                </h1>
                
                <p className="text-lg md:text-xl text-[#EAE7DD]/70 leading-relaxed max-w-2xl mx-auto mb-10">
                    Instant rooftop solar panel verification & yield estimation using high-resolution satellite imagery with GPU acceleration.
                </p>

                <motion.button 
                    onClick={onStart}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="bg-[#EAE7DD] text-[#2c1d11] font-bold py-4 px-10 rounded-full text-lg shadow-2xl hover:bg-[#ffffff] hover:shadow-[#99775C]/30 transition-all flex items-center gap-3 mx-auto group border border-[#99775C]/20"
                >
                    Launch Scout <ArrowRight className="w-5 h-5 text-[#99775C] group-hover:translate-x-1 transition-transform" />
                </motion.button>
            </motion.div>

            {/* Features Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-6xl">
                {features.map((feature, idx) => (
                    <motion.div 
                        key={idx}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6, delay: 0.1 * (idx + 1) }}
                        className="p-8 bg-[#181410]/80 border border-[#99775C]/20 rounded-3xl backdrop-blur-xl hover:border-[#99775C]/50 hover:bg-[#1e1914] transition-all group"
                    >
                        <div className="w-12 h-12 rounded-2xl bg-[#99775C]/15 border border-[#99775C]/25 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                            {feature.icon}
                        </div>
                        <h3 className="text-xl font-bold text-[#EAE7DD] mb-3">{feature.title}</h3>
                        <p className="text-sm text-[#EAE7DD]/60 leading-relaxed">
                            {feature.description}
                        </p>
                    </motion.div>
                ))}
            </div>

            {/* Footer Attribution */}
            <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 1, delay: 0.8 }}
                className="mt-20 text-[11px] font-bold text-[#99775C] uppercase tracking-widest text-center flex items-center gap-2 justify-center"
            >
                <span>Supported by Vardhaman College of Engineering</span>
            </motion.div>
        </div>
    )
}

export default LandingPage
