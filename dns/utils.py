import socket
import dnslib
from dnslib import DNSRecord
from dnslib.dns import CLASS, QTYPE

def send_dns_message(query_name, address, port):
    '''
    Función entregada en las capsulas EOL del curso.
    '''
    # Acá ya no tenemos que crear el encabezado porque dnslib lo hace por nosotros, por default pregunta por el tipo A
    qname = query_name
    q = DNSRecord.question(qname)
    server_address = (address, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # lo enviamos, hacemos cast a bytes de lo que resulte de la función pack() sobre el mensaje
        sock.sendto(bytes(q.pack()), server_address)
        # En data quedará la respuesta a nuestra consulta
        data, _ = sock.recvfrom(4096)
        # le pedimos a dnslib que haga el trabajo de parsing por nosotros
        d = DNSRecord.parse(data)
    finally:
        sock.close()
    # Ojo que los datos de la respuesta van en en una estructura de datos
    return d

def find_domain(domain, cache, debug=False):
    '''
    Busca iterativamente la dirección IP del dominio.
    '''
    if debug:
        print("(debug) Dominio a buscar: {}".format(domain))

    if domain in cache:
        print("(cache) {0} es {1}".format(domain, cache[domain].rdata))
        return cache[domain]

    subdomains = domain.split('.')
    subdomains.pop() #the last element is an empty element

    if debug:
        print("(debug) Los subdominios son {}".format(subdomains))

    acumulated_domain = ""
    name_server_domain = "192.33.4.12" #we start in root

    #we iterate through the subdomains till the IP address is found
    #name_server_domain and acumulated_domain are the variables that change in each iteration
    for i in reversed(range(len(subdomains))):
        acumulated_domain = subdomains[i] + "." + acumulated_domain

        if debug:
            print("(debug) Consultando por {0} en {1}".format(acumulated_domain, name_server_domain))

        dns_reply = send_dns_message(acumulated_domain, name_server_domain, 53)

        #we proccess the reply we get
        # header section
        qr_flag = dns_reply.header.get_qr()
        number_of_query_elements = dns_reply.header.q
        number_of_answer_elements = dns_reply.header.a
        number_of_authority_elements = dns_reply.header.auth
        number_of_additional_elements = dns_reply.header.ar
        primary_name_server = ""
        
        # answer section
        if number_of_answer_elements > 0:
            all_resource_records = dns_reply.rr # lista de objetos tipo dnslib.dns.RR
            first_answer = dns_reply.get_a() # primer objeto en la lista all_resource_records
            domain_name_in_answer = first_answer.get_rname() # nombre de dominio por el cual se está respondiendo
            answer_class = CLASS.get(first_answer.rclass)
            answer_type = QTYPE.get(first_answer.rtype)
            answer_rdata = first_answer.rdata # rdata asociada a la respuesta
            
            print("{0} es {1}".format(acumulated_domain, answer_rdata))
            #we add the link to the cache
            cache[acumulated_domain] = first_answer
            return first_answer

        # authority section
        if number_of_authority_elements > 0:
            authority_section_list = dns_reply.auth # contiene un total de number_of_authority_elements
            authority_section_RR_0 = authority_section_list[0] # objeto tipo dnslib.dns.RR

            authority_section_0_rdata = authority_section_RR_0.rdata
            # si recibimos auth_type = 'SOA' este es un objeto tipo dnslib.dns.SOA
            if isinstance(authority_section_0_rdata, dnslib.dns.SOA):
                primary_name_server = authority_section_0_rdata.get_mname()  # servidor de nombre primario

            elif isinstance(authority_section_0_rdata, dnslib.dns.NS): # si en vez de SOA recibimos un registro tipo NS
                name_server_domain = authority_section_0_rdata.__str__() # entonces authority_section_0_rdata contiene el nombre de dominio del primer servidor de nombre de la lista
        
    return "Address not found"