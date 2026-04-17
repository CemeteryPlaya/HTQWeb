/**
 * WebRTC Video/Audio Stream Diagnostic Tool
 * 
 * Этот скрипт помогает диагностировать проблемы с видео/аудио потоками
 * между клиентами в вашей SFU-based видеоконференции.
 * 
 * ЗАПУСК:
 * 1. Откройте консоль разработчика в браузере (F12)
 * 2. Вставьте этот код в консоль на странице конференции
 * 3. Нажмите Enter
 * 4. Следуйте инструкциям в консоли
 */

(function WebRTCDiagnostic() {
  console.log('%c🔍 WebRTC Video/Audio Diagnostic Tool', 'font-size: 16px; font-weight: bold; color: #4CAF50;');
  console.log('%cЗапуск диагностики проблем с медиапотоками...', 'font-size: 12px; color: #2196F3;');

  // 1. Проверка ICE кандидатов
  function checkIceCandidates() {
    console.group('%c📡 Шаг 1: Проверка ICE кандидатов', 'font-size: 14px; color: #FF9800;');
    
    const hasTurn = window.location.search.includes('turn') || 
                    localStorage.getItem('VITE_TURN_URLS');
    
    console.log('✓ TURN сервер настроен:', hasTurn ? 'ДА' : 'НЕТ (может быть проблемой за NAT)');
    console.log('✓ Текущий хост:', window.location.hostname);
    console.log('✓ Протокол:', window.location.protocol);
    console.log('✓ Secure context:', window.isSecureContext ? 'ДА' : 'НЕТ (критично для камеры/микрофона)');
    
    if (!window.isSecureContext && window.location.hostname !== 'localhost') {
      console.warn('⚠️ ВНИМАНИЕ: Для работы камеры/микрофона нужен HTTPS или localhost!');
    }
    
    console.groupEnd();
  }

  // 2. Проверка MediaStream треков
  function checkMediaStreams() {
    console.group('%c🎥 Шаг 2: Проверка локальных медиапотоков', 'font-size: 14px; color: #9C27B0;');
    
    const videoElements = document.querySelectorAll('video[autoplay]');
    const audioElements = document.querySelectorAll('audio[autoplay]');
    
    console.log(`✓ Найдено <video> элементов: ${videoElements.length}`);
    console.log(`✓ Найдено <audio> элементов: ${audioElements.length}`);
    
    videoElements.forEach((video, idx) => {
      const stream = video.srcObject;
      if (stream instanceof MediaStream) {
        const videoTracks = stream.getVideoTracks();
        const audioTracks = stream.getAudioTracks();
        
        console.log(`  Video #${idx}:`);
        console.log(`    - Видео треков: ${videoTracks.length}`);
        videoTracks.forEach(track => {
          console.log(`      * ${track.label}: enabled=${track.enabled}, muted=${track.muted}, readyState=${track.readyState}`);
        });
        console.log(`    - Аудио треков: ${audioTracks.length}`);
        audioTracks.forEach(track => {
          console.log(`      * ${track.label}: enabled=${track.enabled}, muted=${track.muted}, readyState=${track.readyState}`);
        });
      } else {
        console.log(`  Video #${idx}: srcObject не установлен`);
      }
    });
    
    console.groupEnd();
  }

  // 3. Проверка WebRTC соединений (PeerConnection stats)
  async function checkPeerConnections() {
    console.group('%c🔗 Шаг 3: Проверка WebRTC соединений', 'font-size: 14px; color: #F44336;');
    
    // Пытаемся найти глобальные объекты MediaEngine
    const mediaEngineKeys = Object.keys(window).filter(k => 
      k.includes('MediaEngine') || k.includes('WebRTC') || k.includes('mediaEngine')
    );
    
    console.log('✓ Найдено WebRTC объектов в window:', mediaEngineKeys.length);
    
    // Ищем активные PeerConnection через DevTools
    console.log('💡 Для просмотра PeerConnection статистики:');
    console.log('   1. Откройте chrome://webrtc-internals (Chrome)');
    console.log('   2. Или about:webrtc (Firefox)');
    console.log('   3. Найдите активные соединения с вашим SFU');
    
    console.groupEnd();
  }

  // 4. Проверка сетевого подключения к SFU
  function checkSfuConnection() {
    console.group('%c🌐 Шаг 4: Проверка подключения к SFU', 'font-size: 14px; color: #607D8B;');
    
    const wsConnections = Object.keys(window).filter(k => 
      k.includes('WebSocket') || k.includes('Signaling')
    );
    
    console.log('✓ Signaling объектов в window:', wsConnections.length);
    
    // Проверяем активные WebSocket соединения
    if (performance.getEntriesByType) {
      const wsEntries = performance.getEntriesByType('resource').filter(
        entry => entry.name.includes('ws://') || entry.name.includes('wss://')
      );
      console.log('✓ WebSocket ресурсов найдено:', wsEntries.length);
      wsEntries.forEach(entry => {
        console.log(`  - ${entry.name} (${entry.duration.toFixed(0)}ms)`);
      });
    }
    
    console.groupEnd();
  }

  // 5. Проверка Consumer состояния
  function checkConsumerState() {
    console.group('%c📊 Шаг 5: Проверка состояния Consumer\'ов', 'font-size: 14px; color: #795548;');
    
    // Ищем remoteStreams в глобальной области
    const reactInternals = Array.from(document.querySelectorAll('*')).find(el => 
      el._reactRootContainer || el.__reactFiber$
    );
    
    if (reactInternals) {
      console.log('✓ React приложение найдено');
      console.log('💡 Проверьте React DevTools для просмотра state.remoteStreams');
    }
    
    console.groupEnd();
  }

  // 6. Тест входящего видео
  async function testIncomingVideo() {
    console.group('%c🎬 Шаг 6: Тест входящего видео потока', 'font-size: 14px; color: #E91E63;');
    
    const remoteVideos = Array.from(document.querySelectorAll('video')).filter(v => 
      !v.muted && v.srcObject instanceof MediaStream &&
      v.srcObject.getVideoTracks().length > 0
    );
    
    console.log(`✓ Найдено remote <video> элементов: ${remoteVideos.length}`);
    
    if (remoteVideos.length === 0) {
      console.error('❌ ПРОБЛЕМА: Нет удаленных видео потоков!');
      console.log('💡 Возможные причины:');
      console.log('   1. ICE соединение не установлено (проверьте firewall/NAT)');
      console.log('   2. DTLS handshake провалился (проверьте сертификаты)');
      console.log('   3. Consumer не был создан на сервере (проверьте логи SFU)');
      console.log('   4. Кодеки не совпадают (проверьте codec negotiation)');
    } else {
      remoteVideos.forEach((video, idx) => {
        const stream = video.srcObject;
        const videoTrack = stream.getVideoTracks()[0];
        console.log(`  Remote Video #${idx}:`);
        console.log(`    - Track readyState: ${videoTrack.readyState}`);
        console.log(`    - Track enabled: ${videoTrack.enabled}`);
        console.log(`    - Video element paused: ${video.paused}`);
        console.log(`    - Video muted: ${video.muted}`);
        
        if (videoTrack.readyState === 'ended') {
          console.warn('    ⚠️ Трек завершен - видео не будет отображаться');
        }
      });
    }
    
    console.groupEnd();
  }

  // 7. Рекомендации по исправлению
  function printRecommendations() {
    console.group('%c💡 Рекомендации по исправлению проблем', 'font-size: 14px; font-weight: bold; color: #4CAF50;');
    
    console.log('%c1. ПРОБЛЕМА: Видео не отображается на удаленном компьютере', 'font-weight: bold;');
    console.log('   РЕШЕНИЕ:');
    console.log('   a) Проверьте что SFU имеет правильный WEBRTC_ANNOUNCED_IP');
    console.log('   b) Убедитесь что порт 44444 (UDP/TCP) открыт в firewall');
    console.log('   c) Для TCP_TUNNEL_MODE убедитесь что туннель работает');
    console.log('   d) Проверьте логи SFU на ошибки "DTLS failed" или "ICE failed"');
    
    console.log('');
    console.log('%c2. ПРОБЛЕМА: Аудио работает, видео нет', 'font-weight: bold;');
    console.log('   РЕШЕНИЕ:');
    console.log('   a) Проверьте codec negotiation (VP8/H264 совместимость)');
    console.log('   b) Проверьте что video track не muted на sending стороне');
    console.log('   c) Убедитесь что consumer был создан (SFU логи)');
    console.log('   d) Проверьте что recvPc.setRemoteDescription() прошел успешно');
    
    console.log('');
    console.log('%c3. ПРОБЛЕМА: Черный экран вместо видео', 'font-weight: bold;');
    console.log('   РЕШЕНИЕ:');
    console.log('   a) Видео элемент должен иметь autoplay + playsInline');
    console.log('   b) Проверьте что track.readyState === "live"');
    console.log('   c) Проверьте что stream.getVideoTracks().length > 0');
    console.log('   d) Убедитесь что video.play() вызван без ошибок');
    
    console.log('');
    console.log('%c4. ПРОБЛЕМА: Нет аудио на удаленной стороне', 'font-weight: bold;');
    console.log('   РЕШЕНИЕ:');
    console.log('   a) Проверьте что audio track не muted');
    console.log('   b) Для autoplay аудио нужна пользовательская интеракция');
    console.log('   c) Проверьте кнопку "Включить звук" в UI');
    console.log('   d) Убедитесь что consumer.resume() вызван на сервере');
    
    console.log('');
    console.log('%c5. ОБЩИЕ РЕКОМЕНДАЦИИ:', 'font-weight: bold;');
    console.log('   a) Откройте chrome://webrtc-internals для детальной статистики');
    console.log('   b) Проверьте SFU логи на предмет ошибок ICE/DTLS');
    console.log('   c) Убедитесь что firewall не блокирует UDP/TCP порты');
    console.log('   d) Для тестов используйте localhost или HTTPS домен');
    console.log('   e) Проверьте что TURN сервер доступен (если нужен)');
    
    console.groupEnd();
  }

  // Запуск всех проверок
  console.log('');
  checkIceCandidates();
  checkMediaStreams();
  checkSfuConnection();
  checkConsumerState();
  testIncomingVideo();
  printRecommendations();
  
  console.log('');
  console.log('%c✅ Диагностика завершена!', 'font-size: 14px; font-weight: bold; color: #4CAF50;');
  console.log('%cПроверьте выводы выше и следуйте рекомендациям.', 'font-size: 12px; color: #2196F3;');
  
  // Возвращаем объект с утилитами для дальнейшего использования
  return {
    checkIceCandidates,
    checkMediaStreams,
    testIncomingVideo,
    printRecommendations,
    
    // Утилита для проверки video элемента
    inspectVideoElement: (selector = 'video') => {
      const videos = document.querySelectorAll(selector);
      console.group('Video Element Inspector');
      videos.forEach((video, idx) => {
        console.log(`Video #${idx}:`, {
          srcObject: video.srcObject,
          src: video.src,
          readyState: video.readyState,
          paused: video.paused,
          muted: video.muted,
          volume: video.volume,
          videoTracks: video.srcObject?.getVideoTracks().length || 0,
          audioTracks: video.srcObject?.getAudioTracks().length || 0,
        });
      });
      console.groupEnd();
    },
    
    // Утилита для проверки MediaStream
    inspectMediaStream: (streamIndex = 0) => {
      const videos = document.querySelectorAll('video');
      if (videos.length <= streamIndex) {
        console.error(`Video element #${streamIndex} not found`);
        return;
      }
      
      const stream = videos[streamIndex].srcObject;
      if (!(stream instanceof MediaStream)) {
        console.error('srcObject is not a MediaStream');
        return;
      }
      
      console.group(`MediaStream #${streamIndex} Inspector`);
      console.log('ID:', stream.id);
      console.log('Video Tracks:', stream.getVideoTracks());
      console.log('Audio Tracks:', stream.getAudioTracks());
      console.log('Active:', stream.active);
      console.groupEnd();
    }
  };
})();
