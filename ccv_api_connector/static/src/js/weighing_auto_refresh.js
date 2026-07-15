/** @odoo-module **/
import { FormRenderer } from "@web/views/form/form_renderer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { deserializeDateTime, deserializeDate } from "@web/core/l10n/dates"; // Import bộ giải mã ngày tháng


patch(FormRenderer.prototype, "ccv_weighing_auto_refresh_renderer", {
    setup() {
        this._super(...arguments);
        this.orm = useService("orm");
        this.actionService = useService("action");

        try {
            this.busService = useService("bus_service");
            const onNotification = this._onBusNotification.bind(this);
            this.busService.addEventListener("notification", onNotification);
            this.busService.addChannel("ccv_tts_channel");

            onWillUnmount(() => {
                this.busService.removeEventListener("notification", onNotification);
            });
        } catch (e) {
            console.warn("Bus service not available", e);
        }

        const model = this.props.record.resModel;
        if (model === "sale.vehicle.in.out.line") {
            this._startPolling();
        } else if (model === "mrp.production") {
            this._startPollingMrpProduction();
        } else if (model === "sale.vehicle.in.out") {
            this._startPollingVehicleInOut();
        }
    },

    _onBusNotification({ detail: notifications }) {
        for (const { payload, type } of notifications) {
            if (type === "ccv_tts_speak") {
                const model = this.props.record.resModel;
                if (model === "sale.vehicle.in.out") {
                    if (this.props.record.data.ra_loa && this.props.record.resId === payload.vehicle_id) {
                        this._speakText(payload.text);
                    }
                }
            }
        }
    },

    _speakText(text) {
        if (!('speechSynthesis' in window)) {
            console.warn("Trình duyệt không hỗ trợ Web Speech API.");
            return;
        }

        // Xử lý text: Thay dấu phẩy thành dấu chấm để ép trình đọc ngắt quãng rõ ràng
        let processedText = text.replace(/,/g, '. ');
        
        // Tách rời các ký tự của biển số xe để đọc thật chậm và rõ ràng từng chữ/số
        // Biển số luôn nằm giữa chữ "biển số" và chữ "đã" hoặc "mời" trong luồng code Python
        // Chèn nhiều dấu chấm (. . .) giữa các ký tự để TTS nghỉ hơi lâu hơn
        processedText = processedText.replace(/(biển số[\.,]?\s*)([A-Z0-9\-\.\s]+?)(?=\s*(đã|mời))/gi, function(match, prefix, plate) {
            let spacedPlate = plate.replace(/[^A-Z0-9]/gi, '').split('').join('. . . ');
            return prefix + " . . " + spacedPlate + " . . . ";
        });

        const setVoiceAndSpeak = () => {
            const voices = window.speechSynthesis.getVoices();
            console.log("=== DANH SÁCH TẤT CẢ GIỌNG TIẾNG VIỆT TRÊN MÁY BẠN ===");
            let viVoices = voices.filter(v => v.lang.includes('vi-VN') || v.lang.includes('vi'));
            viVoices.forEach(v => console.log("- ", v.name, v.lang, v.localService ? "(Local)" : "(Online)"));
            
            // Ưu tiên tìm các từ khóa giọng nữ (Ví dụ: Google Tiếng Việt, Microsoft HoaiMy Online)
            const femaleKeywords = ['hoaimy', 'linh', 'female', 'google'];
            let viVoice = viVoices.find(v => femaleKeywords.some(kw => v.name.toLowerCase().includes(kw)));
            
            if (viVoice) {
                // NẾU CÓ GIỌNG NỮ TRÊN TRÌNH DUYỆT -> ĐỌC BÌNH THƯỜNG
                console.log("=> ĐÃ CHỌN GIỌNG NỮ:", viVoice.name);
                const utterance = new SpeechSynthesisUtterance(processedText);
                utterance.lang = 'vi-VN';
                utterance.voice = viVoice;
                utterance.rate = 0.85; // Giảm tốc độ đọc xuống một chút để nghe rõ hơn
                window.speechSynthesis.speak(utterance);
            } else {
                // NẾU KHÔNG CÓ GIỌNG NỮ (CHỈ CÓ MICROSOFT AN HOẶC KHÔNG CÓ GÌ)
                // -> Gọi API ngoài để lấy giọng Nữ của Google (Google Translate TTS)
                console.log("=> KHÔNG TÌM THẤY GIỌNG NỮ TRÊN TRÌNH DUYỆT, CHUYỂN SANG DÙNG GOOGLE TRANSLATE API (GIỌNG NỮ)");
                
                // Cắt ngắn text dưới 400 ký tự để API xử lý tốt
                let safeText = processedText;
                if (safeText.length > 400) safeText = safeText.substring(0, 400);

                // Đổi sang dùng ResponsiveVoice API (Hệ thống Text-to-Speech mở rất uy tín, không chặn CORS, luôn ra giọng Nữ chuẩn)
                // Giảm rate xuống 0.45 để đọc chậm hơn
                const url = `https://code.responsivevoice.org/getvoice.php?t=${encodeURIComponent(safeText)}&tl=vi&sv=g1&vn=&pitch=0.5&rate=0.45&vol=1`;
                const audio = new Audio(url);
                
                audio.play().catch(e => {
                    console.warn("Lỗi phát audio từ Google API, quay về dùng giọng máy mặc định:", e);
                    // Fallback lần cuối cùng nếu mạng chặn API google
                    const utterance = new SpeechSynthesisUtterance(processedText);
                    utterance.lang = 'vi-VN';
                    utterance.rate = 0.85;
                    let fallbackVoice = viVoices.find(v => !v.name.toLowerCase().includes('an')) || viVoices[0];
                    if (fallbackVoice) utterance.voice = fallbackVoice;
                    window.speechSynthesis.speak(utterance);
                });
            }
        };

        const currentVoices = window.speechSynthesis.getVoices();
        const hasFemaleVoice = currentVoices.some(v => 
            (v.lang.includes('vi-VN') || v.lang.includes('vi')) && 
            ['hoaimy', 'linh', 'female', 'google'].some(kw => v.name.toLowerCase().includes(kw))
        );

        if (!hasFemaleVoice) {
            let isSpoken = false;
            
            const onVoicesChanged = () => {
                if (isSpoken) return;
                isSpoken = true;
                window.speechSynthesis.removeEventListener('voiceschanged', onVoicesChanged);
                setVoiceAndSpeak();
            };
            
            window.speechSynthesis.addEventListener('voiceschanged', onVoicesChanged);
            
            // Timeout chờ giọng online của trình duyệt
            setTimeout(() => {
                if (!isSpoken) {
                    isSpoken = true;
                    window.speechSynthesis.removeEventListener('voiceschanged', onVoicesChanged);
                    setVoiceAndSpeak();
                }
            }, 1000);
        } else {
            setVoiceAndSpeak();
        }
    },

    _startPollingVehicleInOut() {
        console.log("[SmartWeight] Bắt đầu Poll cho VehicleInOut ID:", this.props.record.resId);

        this._pollTimerVehicleInOut = setInterval(async () => {
            const record = this.props.record;
            if (!record || !record.resId) return;

            try {
                // Lấy danh sách các dòng xe đang hiển thị
                const lines = record.data.line_ids && record.data.line_ids.records;
                if (!lines || lines.length === 0) {
                    console.log("[SmartWeight] Bắt đầu Poll cho VehicleInOut ID 00:", this.props.record.resId);
                    return;
                }


                const lineIds = lines.map(r => r.resId).filter(id => id);
                if (lineIds.length === 0) {
                    console.log("[SmartWeight] Bắt đầu Poll cho VehicleInOut ID 11:", this.props.record.resId);
                    return;
                }

                // Tải dữ liệu mới nhất của các dòng từ server
                const serverData = await this.orm.read(
                    "sale.vehicle.in.out.line",
                    lineIds,
                    ["canxe_status", "status", "weighing_tl_hang", "weighing_tl_lan1", "weighing_tl_lan2", "quantity"]
                );

                let hasChanged = false;
                for (const newData of serverData) {
                    const lineRecord = lines.find(r => r.resId === newData.id);
                    if (lineRecord && !lineRecord.isDirty) {
                        let changes = {};
                        let lineHasChanged = false;
                        for (const field of ["canxe_status", "status", "weighing_tl_hang", "weighing_tl_lan1", "weighing_tl_lan2", "quantity"]) {
                            if (field in lineRecord.data && lineRecord.data[field] !== newData[field]) {
                                changes[field] = newData[field];
                                lineHasChanged = true;
                            }
                        }
                        if (lineHasChanged) {
                            await lineRecord.update(changes);
                            hasChanged = true;
                        }
                    }
                }

                if (hasChanged) {
                    console.log("[SmartWeight] Bắt đầu Poll cho VehicleInOut ID 22", this.props.record.resId);

                    this.render();
                }
            } catch (err) {
                console.error("[SmartWeight] Lỗi Poll VehicleInOut lines:", err);
            }
        }, 20000); // 20 giây

        onWillUnmount(() => {
            if (this._pollTimerVehicleInOut) {
                clearInterval(this._pollTimerVehicleInOut);
            }
        });
    },

    _startPollingMrpProduction() {
        console.log("[SmartWeight] Bắt đầu Poll cho MRP Production ID:", this.props.record.resId);

        this._pollTimerMrp = setInterval(async () => {
            const record = this.props.record;
            if (!record || !record.resId) return;

            try {
                const recordId = record.resId;
                const serverData = await this.orm.read(
                    "mrp.production",
                    [recordId],
                    ["state_weighing", "weighing_total", "weighing_counter", "bag_number"]
                );

                if (!serverData || serverData.length === 0) return;

                const newData = serverData[0];
                const oldData = record.data;

                // Kiểm tra xem có bất kỳ thay đổi nào về trạng thái, khối lượng hoặc số bao không
                const hasChanged = (
                    oldData.state_weighing !== newData.state_weighing ||
                    oldData.weighing_total !== newData.weighing_total ||
                    oldData.weighing_counter !== newData.weighing_counter
                );

                if (hasChanged) {
                    await record.update(newData);
                    this.render();
                }
            } catch (err) {
                console.error("[SmartWeight] Lỗi Poll MRP Production:", err);
            }
        }, 3000);

        onWillUnmount(() => {
            if (this._pollTimerMrp) {
                clearInterval(this._pollTimerMrp);
            }
        });
    },

    _startPolling() {
        console.log("[SmartWeight] Bắt đầu Poll cho ID:", this.props.record.resId);

        this._pollTimer = setInterval(async () => {
            const record = this.props.record;
            if (!record || !record.resId) return;

            try {
                const recordId = record.resId;
                const serverData = await this.orm.read(
                    "sale.vehicle.in.out.line",
                    [recordId],
                    ["weighing_so_phieu", "weighing_tl_lan1", "weighing_tl_lan2",
                        "weighing_tl_hang", "weighing_ngay_can_1", "weighing_ngay_can_2",
                        "weighing_nhan_vien", "weighing_nhan_vien_bam_can", "weighing_is_export", "weighing_order_id",
                        "weighing_tl_bao_bi", "weighing_tl_sau_tru_bao_bi", "weighing_history_ids"]
                );

                if (!serverData || serverData.length === 0) return;

                const newData = serverData[0];
                const oldVal = (record.data.weighing_tl_hang || "").toString().trim();
                const newVal = (newData.weighing_tl_hang || "").toString().trim();

                const oldVal1 = (record.data.weighing_tl_lan1 || "").toString().trim();
                const newVal1 = (newData.weighing_tl_lan1 || "").toString().trim();

                const oldVal2 = (record.data.weighing_tl_lan2 || "").toString().trim();
                const newVal2 = (newData.weighing_tl_lan2 || "").toString().trim();

                if (oldVal !== newVal || oldVal1 !== newVal1 || oldVal2 !== newVal2) {

                    if (newData.weighing_ngay_can_1) {
                        newData.weighing_ngay_can_1 = deserializeDateTime(newData.weighing_ngay_can_1);
                    }
                    if (newData.weighing_ngay_can_2) {
                        newData.weighing_ngay_can_2 = deserializeDateTime(newData.weighing_ngay_can_2);
                    }

                    await record.update(newData);

                    this.render();
                }
            } catch (err) {
                console.error("[SmartWeight] Lỗi Poll:", err);
            }
        }, 3000);

        onWillUnmount(() => {
            if (this._pollTimer) {
                clearInterval(this._pollTimer);
            }
        });
    }
});
