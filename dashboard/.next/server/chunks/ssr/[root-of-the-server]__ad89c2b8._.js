module.exports = [
"[externals]/next/dist/compiled/next-server/app-page-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-page-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[project]/src/components/ThemeProvider.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "ThemeProvider",
    ()=>ThemeProvider,
    "useTheme",
    ()=>useTheme
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
'use client';
;
;
const ThemeContext = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["createContext"])(undefined);
function ThemeProvider({ children }) {
    const [theme, setTheme] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])('light');
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        // Check for saved theme preference or default to light mode
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            setTheme(savedTheme);
        } else {
            // Check system preference
            const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            setTheme(systemPrefersDark ? 'dark' : 'light');
        }
    }, []);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        // Apply theme to document
        const root = document.documentElement;
        if (theme === 'dark') {
            root.classList.add('dark');
        } else {
            root.classList.remove('dark');
        }
        // Save theme preference
        localStorage.setItem('theme', theme);
    }, [
        theme
    ]);
    const toggleTheme = ()=>{
        setTheme((prev)=>prev === 'light' ? 'dark' : 'light');
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(ThemeContext.Provider, {
        value: {
            theme,
            toggleTheme
        },
        children: children
    }, void 0, false, {
        fileName: "[project]/src/components/ThemeProvider.tsx",
        lineNumber: 47,
        columnNumber: 5
    }, this);
}
function useTheme() {
    const context = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useContext"])(ThemeContext);
    if (context === undefined) {
        throw new Error('useTheme must be used within a ThemeProvider');
    }
    return context;
}
}),
"[project]/src/components/UnitsProvider.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "UnitsProvider",
    ()=>UnitsProvider,
    "useUnits",
    ()=>useUnits
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
'use client';
;
;
const UnitsContext = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["createContext"])(undefined);
function UnitsProvider({ children }) {
    const [unitSystem, setUnitSystem] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])('metric');
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        // Check for saved unit preference
        const savedUnits = localStorage.getItem('unitSystem');
        if (savedUnits) {
            setUnitSystem(savedUnits);
        } else {
            // Default to metric for international users, imperial for US
            const isUS = Intl.DateTimeFormat().resolvedOptions().timeZone?.includes('America');
            setUnitSystem(isUS ? 'imperial' : 'metric');
        }
    }, []);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        // Save unit preference
        localStorage.setItem('unitSystem', unitSystem);
    }, [
        unitSystem
    ]);
    const toggleUnits = ()=>{
        setUnitSystem((prev)=>prev === 'metric' ? 'imperial' : 'metric');
    };
    const convertTemperature = (celsius)=>{
        return unitSystem === 'metric' ? celsius : celsius * 9 / 5 + 32;
    };
    const convertWindSpeed = (ms)=>{
        return unitSystem === 'metric' ? ms : ms * 2.237 // m/s to mph
        ;
    };
    const formatTemperature = (celsius)=>{
        const converted = convertTemperature(celsius);
        const unit = unitSystem === 'metric' ? '°C' : '°F';
        return `${converted.toFixed(1)}${unit}`;
    };
    const formatWindSpeed = (ms)=>{
        const converted = convertWindSpeed(ms);
        const unit = unitSystem === 'metric' ? 'm/s' : 'mph';
        return `${converted.toFixed(1)} ${unit}`;
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(UnitsContext.Provider, {
        value: {
            unitSystem,
            toggleUnits,
            convertTemperature,
            convertWindSpeed,
            formatTemperature,
            formatWindSpeed
        },
        children: children
    }, void 0, false, {
        fileName: "[project]/src/components/UnitsProvider.tsx",
        lineNumber: 63,
        columnNumber: 5
    }, this);
}
function useUnits() {
    const context = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useContext"])(UnitsContext);
    if (context === undefined) {
        throw new Error('useUnits must be used within a UnitsProvider');
    }
    return context;
}
}),
"[project]/src/components/RegionalProvider.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "CAISO_ZONES",
    ()=>CAISO_ZONES,
    "RegionalProvider",
    ()=>RegionalProvider,
    "ZONE_CATEGORIES",
    ()=>ZONE_CATEGORIES,
    "useRegional",
    ()=>useRegional
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
'use client';
;
;
const CAISO_ZONES = {
    STATEWIDE: {
        name: 'STATEWIDE',
        full_name: 'California Statewide',
        latitude: 36.7783,
        longitude: -119.4179,
        major_city: 'California',
        description: 'Aggregated statewide power demand across all CAISO zones',
        load_weight: 1.0,
        climate_region: 'Mixed'
    },
    NP15: {
        name: 'NP15',
        full_name: 'Northern California',
        latitude: 37.7749,
        longitude: -122.4194,
        major_city: 'Northern CA',
        description: 'All of Northern California (PG&E territory north of Path 15)',
        load_weight: 0.42,
        climate_region: 'Mediterranean coastal'
    },
    ZP26: {
        name: 'ZP26',
        full_name: 'Fresno/Central Valley',
        latitude: 36.7378,
        longitude: -119.7871,
        major_city: 'Fresno',
        description: 'Central Valley region, agricultural areas',
        load_weight: 0.08,
        climate_region: 'Hot semi-arid'
    },
    SCE: {
        name: 'SCE',
        full_name: 'Southern California Edison',
        latitude: 34.0522,
        longitude: -118.2437,
        major_city: 'SCE Territory',
        description: 'Southern California Edison utility territory (part of LA metro)',
        load_weight: 0.43,
        climate_region: 'Mediterranean/semi-arid'
    },
    SP15: {
        name: 'SP15',
        full_name: 'LADWP Territory',
        latitude: 34.0522,
        longitude: -118.2437,
        major_city: 'LADWP Territory',
        description: 'Los Angeles Department of Water and Power service area (part of LA metro)',
        load_weight: 0.13,
        climate_region: 'Mediterranean/semi-arid'
    },
    LA_METRO: {
        name: 'LA_METRO',
        full_name: 'Los Angeles Metro Area',
        latitude: 34.0522,
        longitude: -118.2437,
        major_city: 'Los Angeles',
        description: 'Combined LA metropolitan area (SCE + LADWP territories)',
        load_weight: 0.68,
        climate_region: 'Mediterranean/semi-arid'
    },
    SDGE: {
        name: 'SDGE',
        full_name: 'San Diego Gas & Electric',
        latitude: 32.7157,
        longitude: -117.1611,
        major_city: 'San Diego',
        description: 'San Diego County and Imperial Valley',
        load_weight: 0.09,
        climate_region: 'Semi-arid coastal'
    },
    SCE: {
        name: 'SCE',
        full_name: 'Southern California Edison',
        latitude: 34.1478,
        longitude: -117.8265,
        major_city: 'San Bernardino',
        description: 'Inland Empire, Riverside, San Bernardino counties',
        load_weight: 0.15,
        climate_region: 'Hot semi-arid inland'
    },
    PGE_BAY: {
        name: 'PGE_BAY',
        full_name: 'PG&E Bay Area',
        latitude: 37.4419,
        longitude: -122.1430,
        major_city: 'Palo Alto',
        description: 'SF Peninsula, South Bay, Silicon Valley',
        load_weight: 0.05,
        climate_region: 'Mediterranean coastal'
    },
    PGE_VALLEY: {
        name: 'PGE_VALLEY',
        full_name: 'PG&E Central Valley',
        latitude: 37.6391,
        longitude: -120.9969,
        major_city: 'Modesto',
        description: 'Central Valley within PG&E territory',
        load_weight: 0.02,
        climate_region: 'Hot semi-arid'
    },
    SMUD: {
        name: 'SMUD',
        full_name: 'Sacramento Municipal Utility District',
        latitude: 38.5816,
        longitude: -121.4944,
        major_city: 'Sacramento',
        description: 'Sacramento metropolitan area',
        load_weight: 0.02,
        climate_region: 'Mediterranean inland'
    }
};
const ZONE_CATEGORIES = {
    'Major Metro Areas': [
        'STATEWIDE',
        'LA_METRO',
        'NP15',
        'SDGE'
    ],
    'Individual Utilities': [
        'SCE',
        'SP15',
        'PGE_BAY',
        'PGE_VALLEY',
        'SMUD'
    ],
    'Geographic Areas': [
        'ZP26'
    ]
};
const RegionalContext = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["createContext"])(undefined);
function RegionalProvider({ children }) {
    const [selectedZone, setSelectedZone] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])('STATEWIDE');
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        // Check for saved zone preference
        const savedZone = localStorage.getItem('selectedZone');
        if (savedZone && CAISO_ZONES[savedZone]) {
            setSelectedZone(savedZone);
        }
    }, []);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        // Save zone preference
        localStorage.setItem('selectedZone', selectedZone);
    }, [
        selectedZone
    ]);
    const currentZone = CAISO_ZONES[selectedZone];
    const isStatewide = selectedZone === 'STATEWIDE';
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(RegionalContext.Provider, {
        value: {
            selectedZone,
            setSelectedZone,
            currentZone,
            allZones: CAISO_ZONES,
            zoneCategories: ZONE_CATEGORIES,
            isStatewide
        },
        children: children
    }, void 0, false, {
        fileName: "[project]/src/components/RegionalProvider.tsx",
        lineNumber: 168,
        columnNumber: 5
    }, this);
}
function useRegional() {
    const context = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useContext"])(RegionalContext);
    if (context === undefined) {
        throw new Error('useRegional must be used within a RegionalProvider');
    }
    return context;
}
}),
"[project]/node_modules/next/dist/server/route-modules/app-page/module.compiled.js [app-ssr] (ecmascript)", ((__turbopack_context__, module, exports) => {
"use strict";

if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
;
else {
    if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
    ;
    else {
        if ("TURBOPACK compile-time truthy", 1) {
            if ("TURBOPACK compile-time truthy", 1) {
                module.exports = __turbopack_context__.r("[externals]/next/dist/compiled/next-server/app-page-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-page-turbo.runtime.dev.js, cjs)");
            } else //TURBOPACK unreachable
            ;
        } else //TURBOPACK unreachable
        ;
    }
} //# sourceMappingURL=module.compiled.js.map
}),
"[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)", ((__turbopack_context__, module, exports) => {
"use strict";

module.exports = __turbopack_context__.r("[project]/node_modules/next/dist/server/route-modules/app-page/module.compiled.js [app-ssr] (ecmascript)").vendored['react-ssr'].ReactJsxDevRuntime; //# sourceMappingURL=react-jsx-dev-runtime.js.map
}),
"[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)", ((__turbopack_context__, module, exports) => {
"use strict";

module.exports = __turbopack_context__.r("[project]/node_modules/next/dist/server/route-modules/app-page/module.compiled.js [app-ssr] (ecmascript)").vendored['react-ssr'].React; //# sourceMappingURL=react.js.map
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__ad89c2b8._.js.map