import timerList as tm
import slidingWindow as sw
import socket

# (...) acá está el resto de la clase SocketTCP

def send_using_stop_and_wait(self, message):
    message_length = len(message.encode())
    # dividimos el mensaje en trozos de 64 bytes
    data_list = self.chop_message(message, 64)

    # usamos una ventana para que vean como se usa
    initial_seq = self.seq
    data_to_send = sw.SlidingWindow(1, [message_length] + data_list, initial_seq)
    wnd_index = 0

    # creamos un timer usando TimerList, en stop and wait mandamos de a un elemento y necesitamos sólo un timer
    # asi que hacemos que nuestro timer_list sea de tamaño 1 y usamos el timeout de SocketTCP
    timer_list = tm.TimerList(self.timeout, 1)
    t_index = 0

    # partimos armando y enviando el primer segmento
    current_data = data_to_send.get_data(wnd_index)
    current_seq = data_to_send.get_sequence_number(wnd_index)
    current_segment = self.wrap_data_as_segment(current_data, current_seq)
    self.socket_udp.sendto(current_segment.encode(), self.destination_address)

    # y ponemos a correr el timer
    timer_list.start_timer(t_index)

    # para poder usar este timer vamos poner nuestro socket como no bloqueante
    self.socket_udp.setblocking(False)

    # y para manejar esto vamos a necesitar un while True
    while True:
        try:
            # en cada iteración vemos si nuestro timer hizo timeout
            timeouts = timer_list.get_timed_out_timers()
            # si hizo timeout reenviamos el último segmento
            if len(timeouts) > 0:
                self.socket_udp.sendto(current_segment.encode(), self.destination_address)
                # reiniciamos el timer
                timeouts.start_timer(t_index)

            # si no hubo timeout esperamos el ack del receptor
            answer, address = self.socket_udp.recvfrom(self.buff_size)

        except BlockingIOError:
            # como nuestro socket no es bloqueante, si no llega nada entramos aquí y continuamos (hacemos esto en vez de usar threads)
            continue

        else:
            # si no entramos al except (y no hubo otro error) significa que llegó algo!
            # si la respuesta es un ack válido
            if self.is_valid_ack_stop_and_wait(current_segment, answer.decode()):
                # detenemos el timer
                timer_list.stop_timer(t_index)

                # actualizamos el segmento
                data_to_send.move_window(1)
                current_data = data_to_send.get_data(wnd_index)
                
                # si ya mandamos el mensaje completo tenemos current_data == None
                if current_data == None:
                    return

                # si no, actualizamos el número de secuencia y mandamos el nuevo segmento
                else:     
                    current_seq = data_to_send.get_sequence_number(wnd_index)
                    self.seq = current_seq
                    current_segment = self.wrap_data_as_segment(current_data, current_seq)

                    self.socket_udp.sendto(current_segment.encode(), self.destination_address)
        
                    # y ponemos a correr de nuevo el timer
                    timer_list.start_timer(t_index)