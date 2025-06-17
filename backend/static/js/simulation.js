// Pastikan script hanya berjalan jika elemennya ada (jika user sudah login)
if (document.getElementById('get-question-btn')) {
    document.addEventListener('DOMContentLoaded', () => {
        // === Elemen UI ===
        const getQuestionBtn = document.getElementById('get-question-btn');
        const topicInput = document.getElementById('interview-topic');
        const questionText = document.getElementById('question-text');
        const startRecordBtn = document.getElementById('start-record-btn');
        const stopRecordBtn = document.getElementById('stop-record-btn');
        const videoFeed = document.getElementById('video-feed');
        const recIndicator = document.getElementById('rec-indicator');
        const timerDisplay = document.getElementById('timer');
        const liveFeedback = document.getElementById('live-feedback');
        const liveTranscript = document.getElementById('live-transcript');
        const finishBtn = document.getElementById('finish-btn');
        const statusMessage = document.getElementById('status-message');
        
        const setupCard = document.getElementById('setup-card');
        const interviewCard = document.getElementById('interview-card');
        const reportCard = document.getElementById('report-card');
        const finalReportContent = document.getElementById('final-report-content');

        // === Variabel State ===
        let mediaRecorder;
        let recordedChunks = [];
        let stream;
        let timerInterval;
        let chunkInterval;
        let fullTranscript = "";

        // === Fungsi Bantuan ===
        function showStatus(message, type = 'info') {
            statusMessage.textContent = message;
            statusMessage.className = `alert alert-${type}`;
            statusMessage.classList.remove('d-none');
        }
        
        function toggleSpinner(button, show) {
            const spinner = button.querySelector('.spinner-border');
            if (spinner) spinner.classList.toggle('d-none', !show);
            button.disabled = show;
        }

        // === Langkah 1: Mendapatkan Pertanyaan ===
        getQuestionBtn.addEventListener('click', async () => {
            const topic = topicInput.value.trim();
            if (!topic) {
                showStatus('Silakan masukkan topik wawancara.', 'warning');
                return;
            }
            
            toggleSpinner(getQuestionBtn, true);
            showStatus('Sedang membuat pertanyaan untukmu...', 'info');

            try {
                const response = await fetch('/api/interview/generate_question', {
                    method: 'POST',
                    // TAMBAHKAN BAGIAN HEADERS INI
                    headers: { 
                        'Content-Type': 'application/json', 
                        'Authorization': 'Bearer ' + localStorage.getItem('access_token') 
                    },
                    body: JSON.stringify({ topic: topic })
                });
                
                if (response.status === 401) {
                    throw new Error("Sesi Anda telah berakhir. Silakan login kembali.");
                }
                if (!response.ok) {
                    throw new Error(`Server merespons dengan status ${response.status}`);
                }

                const data = await response.json();
                if (data.error) throw new Error(data.details || data.error);

                questionText.textContent = data.question;
                setupCard.classList.add('d-none');
                interviewCard.classList.remove('d-none');
                statusMessage.classList.add('d-none');

            } catch (error) {
                console.error('Error getting question:', error);
                showStatus(`Gagal mendapatkan pertanyaan: ${error.message}`, 'danger');
            } finally {
                toggleSpinner(getQuestionBtn, false);
            }
        });

        // === Langkah 2: Memulai Rekaman ===
        startRecordBtn.addEventListener('click', async () => {
            try {
                stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                videoFeed.srcObject = stream;
                
                mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm; codecs=vp8,opus' });
                
                mediaRecorder.ondataavailable = event => {
                    if (event.data.size > 0) {
                        recordedChunks.push(event.data);
                    }
                };
                
                mediaRecorder.start(2000);
                
                startRecordBtn.classList.add('d-none');
                stopRecordBtn.classList.remove('d-none');
                recIndicator.style.display = 'flex';
                finishBtn.classList.add('d-none');
                
                let seconds = 0;
                timerInterval = setInterval(() => {
                    seconds++;
                    const min = String(Math.floor(seconds / 60)).padStart(2, '0');
                    const sec = String(seconds % 60).padStart(2, '0');
                    timerDisplay.textContent = `${min}:${sec}`;
                }, 1000);

                chunkInterval = setInterval(sendChunkForAnalysis, 4000);

            } catch (error) {
                console.error('Error starting recording:', error);
                showStatus(`Tidak bisa mengakses kamera/mikrofon: ${error.message}. Mohon izinkan akses.`, 'danger');
            }
        });

        // === Langkah 3: Menghentikan Rekaman ===
        stopRecordBtn.addEventListener('click', () => {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }

            clearInterval(timerInterval);
            clearInterval(chunkInterval);
            timerDisplay.textContent = "00:00";
            
            stopRecordBtn.classList.add('d-none');
            startRecordBtn.classList.remove('d-none');
            recIndicator.style.display = 'none';
            if (fullTranscript.length > 0) {
                finishBtn.classList.remove('d-none');
            }
        });

        // === Langkah 4: Mengirim Chunk untuk Analisis Real-time ===
        async function sendChunkForAnalysis() {
            if (recordedChunks.length === 0) return;

            const canvas = document.createElement('canvas');
            canvas.width = videoFeed.videoWidth;
            canvas.height = videoFeed.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(videoFeed, 0, 0, canvas.width, canvas.height);
            const videoBase64 = canvas.toDataURL('image/jpeg').split(',')[1];
            
            const audioBlob = new Blob(recordedChunks, { type: 'video/webm' });
            recordedChunks = [];

            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            reader.onloadend = async () => {
                const audioBase64 = reader.result.split(',')[1];
                try {
                    const response = await fetch('/api/interview/analyze_realtime_chunk', {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json', 
                            'Authorization': 'Bearer ' + localStorage.getItem('access_token') 
                        },
                        body: JSON.stringify({ audio: audioBase64, video: videoBase64 })
                    });

                    if (response.status === 401) throw new Error("Sesi Anda telah berakhir. Silakan login kembali.");
                    if (!response.ok) throw new Error(`Server merespons dengan status ${response.status}`);
                    
                    const data = await response.json();
                    if(data.error) throw new Error(data.details || data.error);

                    if (data.live_feedback) liveFeedback.textContent = data.live_feedback;
                    if (data.transcribed_text) {
                        liveTranscript.textContent = data.transcribed_text;
                        fullTranscript += data.transcribed_text + " ";
                    }
                } catch (error) {
                    console.error("Error analyzing chunk:", error);
                    liveFeedback.textContent = `Error: ${error.message}`;
                }
            };
        }
        
        // === Langkah 5: Mendapatkan Laporan Akhir ===
        finishBtn.addEventListener('click', async () => {
            if (!fullTranscript.trim()) {
                showStatus("Tidak ada transkrip untuk dianalisis.", "warning");
                return;
            }

            toggleSpinner(finishBtn, true);
            showStatus('Membuat laporan akhir...', 'info');
            
            try {
                const response = await fetch('/api/interview/save_report', {
                    method: 'POST',
                    // PASTIKAN HEADERS INI SUDAH ADA
                    headers: { 
                        'Content-Type': 'application/json', 
                        'Authorization': 'Bearer ' + localStorage.getItem('access_token') 
                    },
                    // PASTIKAN ANDA MENGIRIM "question" DAN "transcript"
                    body: JSON.stringify({ 
                        transcript: fullTranscript,
                        question: questionText.textContent // <-- KIRIM PERTANYAAN
                    })
                });

                if (response.status === 401) throw new Error("Sesi Anda telah berakhir. Silakan login kembali.");
                if (!response.ok) throw new Error(`Server merespons dengan status ${response.status}`);

                const report = await response.json();
                if(report.error) throw new Error(report.details || report.error);

                finalReportContent.innerHTML = `
                    <div class="row">
                        <div class="col-md-3 text-center">
                            <h4 class="fw-bold">Skor Keseluruhan</h4>
                            <p class="display-4 fw-bold gradient-text">${report.overallScore || 'N/A'}</p>
                        </div>
                        <div class="col-md-9">
                            <h5>Ringkasan</h5>
                            <p class="text-muted">${report.summary || 'Tidak ada ringkasan.'}</p>
                        </div>
                    </div>
                    <hr class="my-4">
                    <h5><i class="fas fa-thumbs-up text-success me-2"></i>Kekuatan Anda</h5>
                    <p class="text-muted">${report.strengthAnalysis || '-'}</p>
                    <h5><i class="fas fa-lightbulb text-warning me-2"></i>Saran Perbaikan</h5>
                    <p class="text-muted">${report.improvementSuggestion || '-'}</p>
                    <h5><i class="fas fa-comment-alt text-info me-2"></i>Contoh Jawaban yang Disarankan</h5>
                    <div class="p-3 bg-light rounded">${report.suggestedAnswerExample || '-'}</div>
                `;
                reportCard.classList.remove('d-none');
                interviewCard.classList.add('d-none');
                statusMessage.classList.add('d-none');
            } catch(error) {
                console.error("Error getting final report:", error);
                showStatus(`Gagal membuat laporan: ${error.message}`, 'danger');
            } finally {
                toggleSpinner(finishBtn, false);
            }
        });
    });
}