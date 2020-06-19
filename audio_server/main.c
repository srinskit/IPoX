#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/in.h>

#define PORT 8080
#define MAXLINE 16384
#define PING_FLAG '0'

int main()
{
	int sockfd;
	char buffer[MAXLINE];
	struct sockaddr_in servaddr, cliaddr, clients[2];

	if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0)
	{
		perror("socket creation failed");
		exit(EXIT_FAILURE);
	}

	memset(&servaddr, 0, sizeof(servaddr));
	memset(&cliaddr, 0, sizeof(cliaddr));
	memset(&clients, 0, sizeof(clients));

	servaddr.sin_family = AF_INET;
	servaddr.sin_addr.s_addr = INADDR_ANY;
	servaddr.sin_port = htons(PORT);

	if (bind(sockfd, (const struct sockaddr *)&servaddr,
			 sizeof(servaddr)) < 0)
	{
		perror("bind failed");
		exit(EXIT_FAILURE);
	}

	int len, n, fill = 0;

	while (1)
	{
		len = sizeof(cliaddr);
		n = recvfrom(sockfd, (char *)buffer, MAXLINE,
					 MSG_WAITALL, (struct sockaddr *)&cliaddr,
					 &len);
		clients[buffer[0] == '1' ? 1 : 0] = cliaddr;
		if (buffer[1] != PING_FLAG)
			sendto(sockfd, (const char *)buffer, n, MSG_CONFIRM,
				   (const struct sockaddr *)(&clients[buffer[0] == '1' ? 0 : 1]), len);
	}
	return 0;
}
